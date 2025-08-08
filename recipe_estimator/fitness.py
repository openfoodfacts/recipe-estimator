import numpy as np

# Tried using numba to improve performance but went slower
# from numba import jit
# from numba.typed import Dict
# from numba.core import types

from .prepare_nutrients import prepare_nutrients

# NOTE: The following is not used at the moment. We currently just minimize the variance from the nominal nutrient value
# and don't use min and max. This gives roughly similar results but is less computation, so faster.

# Penalty function returns zero if the target matches the nominal value and returns
# a positive value based on tolerance_penalty where there is divergence. If the divergence is more than
# the min / max then the steep gradient is used.
# We want the steep_gradient to be proportional to the order of magnitude of the nutrient size
# So the penalty for a nutrient with a nominal value of 1g/100g should increase by the steep_gradient
# for every 1g outside min / max, whereas a nutrient with a nominal value of 1ug/100g should
# have a penalty of steep_gradient times the number of ug outside of the min / max range
#
# penalty
#    ^        *                                               *
#    |         * <----------- steep_gradient --------------> *
#    |          *                                           *
#    |           *                                         *
#    |            *                                       *
#    |             *                                     *
#    |              *                                   *
#    |               ******                          ***  <- tolerance_penalty
#    |                     ******                 ***
#    |                           ******        ***
#    |---------------------------------********------------------------------------------> value
#                    ^                      ^           ^
#                min_value               nom_value   max_value
#
def assign_penalty(
    value, nom_value, tolerance_penalty, min_value, max_value, steep_gradient
):
    if value < min_value:
        return tolerance_penalty + (min_value - value) * steep_gradient

    if value > max_value:
        return tolerance_penalty + (value - max_value) * steep_gradient

    if value > nom_value:
        return tolerance_penalty * (value - nom_value) / (max_value - nom_value)

    if value < nom_value:
        return tolerance_penalty * (nom_value - value) / (nom_value - min_value)

    # Value = nom_value
    return 0


def get_objective_function_args(product):
    leaf_ingredient_count = prepare_nutrients(product, True)
    ingredients = product["ingredients"]
    recipe_estimator = product["recipe_estimator"]
    nutrients = recipe_estimator["nutrients"]

    # For the model we need an array of variables. This will be the quantity of each leaf ingredient to make 100g of product
    # in order. Note the total may be more than 100g to account for loss of mass (typically water) during preparation (e.g. evaporation during cooking)
    # For example, a simple tomato sauce of tomatoes and onions might have a matrix of [120, 50]
    # This is saying we start with 120g of tomatoes and 50g of onions and during cooking we lose 70g mass
    # The constraints we apply are as follows:
    #  - Total of ingredients must add up to at least 100. Expressed as a matrix [1, 1] >= 100
    # The later ingredient must be less than the one before. [1, -1] >= 0. For n ingredients there will be n-1 of these constraints
    # If we are dealing with an ingredient where the next ingredient has sub-ingredients then the earlier ingredient must be greater than
    # or equal to the the sum of the sub-ingredients of the later ingredient. Similarly if the earlier ingredient has sub-ingredients
    # then the sum of its sub-ingredients must be greater than or equal to the next ingredient.
    # For the objective function, for each nutrient we sum the product of the mass of each ingredient and its nutrient proportion
    # and assign a penalty based on its divergence from the nutrient value of the product. We weight this depending on a factor for the nutrient.

    # Leaf ingredients are those that do not have sub-ingredients.
    leaf_ingredients = []
    ingredient_order_previous_indices = []
    ingredient_order_this_indices = []
    bounds = []

    def ingredient_order_constraint(
        start_of_previous_parent, leaf_ingredient_index, sub_ingredient_count
    ):
        # return { 'type': 'ineq', 'fun': lambda x: sum(x[previous_start : this_start : 2]) - sum(x[this_start : this_start + this_count * 2 : 2])}
        previous_ingredient_indices = []
        next_ingredient_indices = []
        for i in range(0, leaf_ingredient_count):
            if i >= start_of_previous_parent and i < leaf_ingredient_index:
                previous_ingredient_indices.append(i)
            if (
                i >= leaf_ingredient_index
                and i < leaf_ingredient_index + sub_ingredient_count
            ):
                next_ingredient_indices.append(i)
        return [previous_ingredient_indices, next_ingredient_indices]

    # Prepare nutrients information in arrays for fast objective function
    nutrient_names = []
    product_nutrients = []
    # Following is an array of nutrients each containing an array of data for that nutrient for each ingredient (not including the lost water leaves)
    nutrient_ingredients_nom = []
    nutrient_ingredients_min = []
    nutrient_ingredients_max = []
    nutrient_weightings = []
    for nutrient_key in nutrients:
        nutrient = nutrients[nutrient_key]

        weighting = nutrient.get("weighting")

        # Skip nutrients that don't have a weighting
        if weighting is None or weighting == 0:
            # print("Skipping nutrient without weight:", nutrient_key)
            continue
        nutrient_names.append(nutrient_key)
        product_nutrients.append(nutrient["product_total"])
        nutrient_weightings.append(weighting)
        nutrient_ingredients_nom.append([])
        nutrient_ingredients_min.append([])
        nutrient_ingredients_max.append([])

    def add_ingredients(
        ingredients, parent_estimate, parent_min_percent, parent_max_percent
    ):
        leaf_ingredients_added = 0
        # Initial estimate of ingredients is a geometric progression where each is half the previous one
        # Sum of a  geometric progression is Sn = a(1 - r^n) / (1 - r)
        # In our case Sn = 100 and r = 0.5 so our first ingredient (a) will be
        # (100 * 0.5) / (1 - 0.5 ^ n)
        num_ingredients = len(ingredients)
        initial_estimate = (parent_estimate * 0.5) / (1 - 0.5 ** num_ingredients)
        for i, ingredient in enumerate(ingredients):
            leaf_ingredient_index = len(leaf_ingredients)

            # If there are, say, 3 ingredients then the 1st can be between 100% and 33%, second can be between 50% and 0%, third can be between 33% and 0%
            # So in general the max percentage is 100% / ingredient_number and the min percentage is 100% / num_ingredients for the first ingredient and 0 for others
            # Where there are sub-ingredients the max percent follows the same formula except replacing 100% with the max percent of the parent
            # For the min percent this only applies to the very first leaf ingredient and needs to consider the number of ingredients in its sub-group
            # along with the total number of ingredients in the root group.
            # For example if a product has 4 ingredients but the first ingredient is a group of 3 ingredients then the overall first ingredient group can't be less than
            # 25% but the first ingredient in that group could be 25 % / 3
            # These rules don't fully hold when evaporation is taken into consideration but that would get very complicated so is ignored for now.
            max_percent = parent_max_percent / (i + 1)
            min_percent = parent_min_percent / num_ingredients if i == 0 else 0

            if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
                sub_ingredient_count = add_ingredients(
                    ingredient["ingredients"],
                    initial_estimate,
                    min_percent,
                    max_percent,
                )
            else:
                # Initial estimate. 0.5 of previous ingredient
                leaf_ingredients.append(ingredient)
                ingredient["index"] = leaf_ingredient_index
                ingredient["initial_estimate"] = initial_estimate
                sub_ingredient_count = 1

                # Set lost water constraint
                water = ingredient["nutrients"].get("water", {})
                maximum_water_content = water.get("percent_nom", 0) * 0.01
                # water_loss_multipliers.append(
                #     water_constraint(leaf_ingredient_index, maximum_water_content)
                # )

                # Assume no more than 50% of the water is lost
                # TODO: See if we can justify this assumption with some product statistics
                maximum_weight = max_percent / (1 - (0.5 * maximum_water_content))
                bounds.append([min_percent, maximum_weight])

                # # Water loss. Initial estimate is zero
                # leaf_ingredients.append(0)
                # maximum_percentages.append(None if maximum_water_content == 1 else maximum_water_content * maximum_weight)

                for n, nutrient_key in enumerate(nutrient_names):
                    ingredient_nutrient = ingredient["nutrients"].get(nutrient_key)
                    if ingredient_nutrient:
                        nutrient_ingredients_nom[n].append(ingredient_nutrient["percent_nom"] / 100)
                        nutrient_ingredients_min[n].append(ingredient_nutrient["percent_min"] / 100)
                        nutrient_ingredients_max[n].append(ingredient_nutrient["percent_max"] / 100)
                    else:
                        # Treat unknown nutrients as having 0% of each nutrient
                        # TODO: Might be able to refine this, e.g. use a nominal small value appropriate to the nutrient type
                        nutrient_ingredients_nom[n].append(0)
                        nutrient_ingredients_min[n].append(0)
                        nutrient_ingredients_max[n].append(0)

            # Set order constraint
            if i > 0:
                # Sum of children must be less than previous ingredient (or sum of its children)
                [previous_ingredient_indices, next_ingredient_indices] = ingredient_order_constraint(
                        start_of_previous_parent,
                        leaf_ingredient_index,
                        sub_ingredient_count,
                    )
                ingredient_order_previous_indices.append(np.array(previous_ingredient_indices))
                ingredient_order_this_indices.append(np.array(next_ingredient_indices))

            initial_estimate /= 2
            leaf_ingredients_added += sub_ingredient_count
            start_of_previous_parent = leaf_ingredient_index
        return leaf_ingredients_added

    add_ingredients(ingredients, 100, 100, 100)
    if len(bounds) == 1:
        if bounds[0][1] == 100:
            # If there is only one ingredient with no known water content the bounds will be 100, 100 which the optimizer doesn't like, so fudge the max a bit
            bounds[0][1] = 105
        else:
            # Can get issues where rounding inside the algorithm makes the initial guess outside of bounds
            # So tweak the lower bound very slightly
            bounds[0][0] = 100 - 1e-10

    # # Total mass of all ingredients less all lost water must be 100g
    # total_mass_multipliers = [0] * leaf_ingredient_count * 2
    # for i in range(0, leaf_ingredient_count * 2):
    #     total_mass_multipliers[i] = -1 if i % 2 else 1

    penalties = {} # Need this if using numba: Dict.empty(key_type=types.unicode_type, value_type=types.float64)
    args = [penalties, np.array(product_nutrients), np.array(nutrient_ingredients_nom), np.array(nutrient_ingredients_min), np.array(nutrient_ingredients_max), np.array(nutrient_weightings), ingredient_order_previous_indices, ingredient_order_this_indices, leaf_ingredient_count]
    return [bounds, leaf_ingredients, args]


NUTRIENT_WITHIN_BOUNDS_PENALTY = 10000
NUTRIENT_OUTSIDE_BOUNDS_PENALTY = 130000
INGREDIENT_BIGGER_THAN_PREVIOUS_PENALTY = 1000000
INGREDIENT_NOT_HALF_PREVIOUS_PENALTY = 10
TOTAL_MASS_LESS_THAN_100_PENALTY = 10000000
TOTAL_MASS_MORE_THAN_100_PENALTY = 100

# TODO: Try using quadratic / cubic penalty functions so that gradients are smoother and may be easier for optimizer to spot path to minimum
# TODO: Use matrix libraries for objective calculations to speed things up
# @jit # pre-compile with numba
def objective(ingredient_percentages, penalties, product_nutrients, nutrient_ingredients_nom, nutrient_ingredients_min, nutrient_ingredients_max, nutrient_weightings, ingredient_order_previous_indices, ingredient_order_this_indices, leaf_ingredient_count):
    nutrient_variance = 0
    # This seems to be a bit faster than for n, nutrient_total in enumerate(product_nutrients)
    num_nutrients = len(product_nutrients)
    for n in range(num_nutrients):
        nutrient_total = product_nutrients[n]
        # nom_nutrient_total_from_ingredients = sum(map(lambda x, y: x * y, ingredient_percentages, nutrient_ingredients_nom[n]))
        # nom_nutrient_total_from_ingredients = sum([ingredient_percentages[i] * nutrient_ingredient_nom for i, nutrient_ingredient_nom, in enumerate(nutrient_ingredients_nom[n])])
        # nom_nutrient_total_from_ingredients = sum(ingredient_percentage * nutrient_ingredient_nom for ingredient_percentage, nutrient_ingredient_nom in zip(ingredient_percentages, nutrient_ingredients_nom[n]))
        # nutrient_ingredients_nom_n = nutrient_ingredients_nom[n]
        nom_nutrient_total_from_ingredients = (ingredient_percentages * nutrient_ingredients_nom[n]).sum()
        # min_nutrient_total_from_ingredients = (ingredient_percentages * nutrient_ingredients_min[n]).sum()
        # max_nutrient_total_from_ingredients = (ingredient_percentages * nutrient_ingredients_max[n]).sum()

        # Factors need to quite large as the algorithms only make tiny changes to the variables to determine gradients
        # TODO: Need to experiment with factors here
        # nutrient_penalty += nutrient_weightings[n] * assign_penalty(
        #     nutrient_total,
        #     nom_nutrient_total_from_ingredients,
        #     NUTRIENT_WITHIN_BOUNDS_PENALTY,
        #     min_nutrient_total_from_ingredients,
        #     max_nutrient_total_from_ingredients,
        #     NUTRIENT_OUTSIDE_BOUNDS_PENALTY,
        # )
        
        nutrient_variance += nutrient_weightings[n] * (nutrient_total - nom_nutrient_total_from_ingredients) ** 2

    nutrient_penalty = NUTRIENT_OUTSIDE_BOUNDS_PENALTY * nutrient_variance

    ingredient_not_half_previous_penalty = 0
    ingredient_more_than_previous_penalty = 0
    # Now add a penalty for the constraints
    num_indices = len(ingredient_order_previous_indices)
    for n in range(num_indices):
        # take and "fancy" indexing seem to perform about the same
        previous_total = ingredient_percentages.take(ingredient_order_previous_indices[n]).sum()
        this_total = ingredient_percentages.take(ingredient_order_this_indices[n]).sum()
        # In the absence of anything else we want this_total to be 50% of the previous_total so we apply a very small penalty
        # for deviations from that. However, once this_total gets bigger than previous_total we want to apply a higher penalty

        # penalty
        #    ^                                        *
        #    |        steep_gradient --------------> *
        #    |                                      *
        #    |                                     *
        #    |                                    *
        #    |                                   *
        #    |                                  *
        #    |*****                            *
        #    |     ******                     *
        #    |           ******        ******
        #    |-----------------********------------------------------------------> this / parent
        #                           ^        ^
        #                          50%      100% (this >= parent)

        if this_total < previous_total:
            ingredient_not_half_previous_penalty += (
                abs(this_total - (previous_total * 0.5))
                * INGREDIENT_NOT_HALF_PREVIOUS_PENALTY
            )
        else:
            # This is greater than previous. Add the above penalty for this = previous
            ingredient_more_than_previous_penalty += (
                0.5 * this_total
            ) * INGREDIENT_NOT_HALF_PREVIOUS_PENALTY
            # And then add a steep gradient for percent above previous
            ingredient_more_than_previous_penalty += (
                this_total - previous_total
            ) * INGREDIENT_BIGGER_THAN_PREVIOUS_PENALTY

    # for multipliers in water_loss_multipliers:
    #     water_loss_test = sum([ingredient_quantity * multipliers[n] for n, ingredient_quantity in enumerate(ingredient_percentages)])
    #     # If the test is negative (water loss is more than the expected maximum water content of the ingredient) then add a moderate penalty
    #     if water_loss_test < 0:
    #         penalty += (-water_loss_test) * 1000

    # Total mass penalty. Scale by number of ingredients so in the same order as other penalties
    total_mass = sum(ingredient_percentages)
    mass_more_than_100_penalty = 0
    mass_less_than_100_penalty = 0
    if total_mass < 100:
        # Add a high penalty as the total mass is less than 100g
        mass_less_than_100_penalty += (
            (100 - total_mass)
            * TOTAL_MASS_LESS_THAN_100_PENALTY
            * leaf_ingredient_count
        )
    else:
        # Add a very small penalty as the mass increases above 100g
        mass_more_than_100_penalty += (
            (total_mass - 100)
            * TOTAL_MASS_MORE_THAN_100_PENALTY
            * leaf_ingredient_count
        )

    # Although we could also model bounds using penalties the optimizers seem to work better if they have bounds

    # for n, maximum_percentage in enumerate(maximum_percentages):
    #     if ingredient_percentages[n] < 0:
    #         # Add a big penalty for negative ingredients
    #         penalty += (-ingredient_percentages[n]) * 100000
    #     if maximum_percentage and ingredient_percentages[n] > maximum_percentage:
    #         # Add a moderate penalty if an ingredient is bigger than what we think it's maximum should be
    #         penalty += (ingredient_percentages[n] - maximum_percentage) * 1000

    penalty = (
        nutrient_penalty
        + ingredient_not_half_previous_penalty
        + ingredient_more_than_previous_penalty
        + mass_more_than_100_penalty
        + mass_less_than_100_penalty
    )
    # These are good for debugging and don't seem to but slow things down a lot
    penalties["nutrient_penalty"] = nutrient_penalty
    penalties["ingredient_not_half_previous_penalty"] = (
        ingredient_not_half_previous_penalty
    )
    penalties["ingredient_more_than_previous_penalty"] = (
        ingredient_more_than_previous_penalty
    )
    penalties["mass_more_than_100_penalty"] = mass_more_than_100_penalty
    penalties["mass_less_than_100_penalty"] = mass_less_than_100_penalty
    penalties["total"] = penalty
    return penalty

