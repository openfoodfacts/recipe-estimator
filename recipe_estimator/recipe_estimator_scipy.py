import sys
import time
import warnings
from scipy.optimize import (
    minimize,
    dual_annealing,
    shgo,
    basinhopping,
    differential_evolution,
    direct,
)

from .prepare_nutrients import prepare_nutrients


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
    ingredient_order_multipliers = []
    water_loss_multipliers = []
    bounds = []

    def water_constraint(ingredient_index, maximum_water_content):
        # return { 'type': 'ineq', 'fun': lambda x: x[i] * maximum_water_content - x[i + 1]}
        ingredient_multipliers = [0] * leaf_ingredient_count * 2
        ingredient_multipliers[ingredient_index] = maximum_water_content
        ingredient_multipliers[ingredient_index + 1] = -1
        return ingredient_multipliers

    def ingredient_order_constraint(
        start_of_previous_parent, leaf_ingredient_index, sub_ingredient_count
    ):
        # return { 'type': 'ineq', 'fun': lambda x: sum(x[previous_start : this_start : 2]) - sum(x[this_start : this_start + this_count * 2 : 2])}
        ingredient_multipliers = [0] * leaf_ingredient_count
        for i in range(0, leaf_ingredient_count):
            if i >= start_of_previous_parent and i < leaf_ingredient_index:
                ingredient_multipliers[i] = 1
            if (
                i >= leaf_ingredient_index
                and i < leaf_ingredient_index + sub_ingredient_count
            ):
                ingredient_multipliers[i] = -1
        return ingredient_multipliers

    # Prepare nutrients information in arrays for fast objective function
    nutrient_names = []
    product_nutrients = []
    # Following is an array of nutrients each containing an array of data for that nutrient for each ingredient (not including the lost water leaves)
    nutrient_ingredients = []
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
        nutrient_ingredients.append([])

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
                        nutrient_ingredients[n].append(
                            {
                                "conf": ingredient_nutrient.get("confidence", "?"),
                                "nom": ingredient_nutrient["percent_nom"] / 100,
                                "min": ingredient_nutrient["percent_min"] / 100,
                                "max": ingredient_nutrient["percent_max"] / 100,
                            }
                        )
                    else:
                        nutrient_ingredients[n].append({"conf": "-"})

            # Set order constraint
            if i > 0:
                # Sum of children must be less than previous ingredient (or sum of its children)
                ingredient_order_multipliers.append(
                    ingredient_order_constraint(
                        start_of_previous_parent,
                        leaf_ingredient_index,
                        sub_ingredient_count,
                    )
                )

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

    args = [{}, product_nutrients, nutrient_ingredients, nutrient_weightings, ingredient_order_multipliers, leaf_ingredient_count]
    return [bounds, leaf_ingredients, args]


NUTRIENT_WITHIN_BOUNDS_PENALTY = 10000
NUTRIENT_OUTSIDE_BOUNDS_PENALTY = 100000
INGREDIENT_BIGGER_THAN_PREVIOUS_PENALTY = 1000000
INGREDIENT_NOT_HALF_PREVIOUS_PENALTY = 10
TOTAL_MASS_LESS_THAN_100_PENALTY = 10000000
TOTAL_MASS_MORE_THAN_100_PENALTY = 100

# TODO: Try using quadratic / cubic penalty functions so that gradients are smoother and may be easier for optimizer to spot path to minimum
# TODO: Use matrix libraries for objective calculations to speed things up
def objective(ingredient_percentages, penalties, product_nutrients, nutrient_ingredients, nutrient_weightings, ingredient_order_multipliers, leaf_ingredient_count):
    nutrient_penalty = 0

    for n, nutrient_total in enumerate(product_nutrients):
        nom_nutrient_total_from_ingredients = 0
        min_nutrient_total_from_ingredients = 0
        max_nutrient_total_from_ingredients = 0
        for i, nutrient_ingredient in enumerate(nutrient_ingredients[n]):
            if nutrient_ingredient["conf"] != "-":
                nom_nutrient_total_from_ingredients += (
                    ingredient_percentages[i] * nutrient_ingredient["nom"]
                )
                min_nutrient_total_from_ingredients += (
                    ingredient_percentages[i] * nutrient_ingredient["min"]
                )
                max_nutrient_total_from_ingredients += (
                    ingredient_percentages[i] * nutrient_ingredient["max"]
                )

        # Factors need to quite large as the algorithms only make tiny changes to the variables to determine gradients
        # TODO: Need to experiment with factors here
        nutrient_penalty += nutrient_weightings[n] * assign_penalty(
            nutrient_total,
            nom_nutrient_total_from_ingredients,
            NUTRIENT_WITHIN_BOUNDS_PENALTY,
            min_nutrient_total_from_ingredients,
            max_nutrient_total_from_ingredients,
            NUTRIENT_OUTSIDE_BOUNDS_PENALTY,
        )

    ingredient_not_half_previous_penalty = 0
    ingredient_more_than_previous_penalty = 0
    # Now add a penalty for the constraints
    for multipliers in ingredient_order_multipliers:
        previous_total = sum(
            [
                ingredient_quantity * multipliers[n]
                for n, ingredient_quantity in enumerate(ingredient_percentages)
                if multipliers[n] > 0
            ]
        )
        this_total = sum(
            [
                ingredient_quantity * -(multipliers[n])
                for n, ingredient_quantity in enumerate(ingredient_percentages)
                if multipliers[n] < 0
            ]
        )
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


# estimate_recipe() uses a linear solver to estimate the quantities of all leaf ingredients (ingredients that don't have child ingredient)
# The solver is used to minimise the difference between the sum of the nutrients in the leaf ingredients and the total nutrients in the product
def estimate_recipe(product):
    current = time.perf_counter()
    [bounds, leaf_ingredients, args] = get_objective_function_args(product)
    MAXITER = 5000
    x0 = [ingredient["initial_estimate"] for ingredient in leaf_ingredients]

    # constraints = [
    #     LinearConstraint(A, lb=0)
    #     for A in ingredient_order_multipliers + water_loss_multipliers
    # ]
    # # For COBYLA can't use eq constraint
    # constraints.append(LinearConstraint(total_mass_multipliers, lb=99.99, ub=100.01))

    # COBYQA is very slow
    # solution = minimize(objective,x,method='COBYLA',bounds=bounds,constraints=cons,options={'maxiter': 10000})
    # solution = minimize(
    #     objective,
    #     leaf_ingredients,
    #     method="SLSQP",
    #     bounds=bounds,
    #     # constraints=constraints,
    # )  # Fastest

    # solution = minimize(
    #     objective,
    #     leaf_ingredients,
    #     method="L-BFGS-B",
    #     bounds=bounds,
    #     # constraints=constraints,
    # )  # Fastest

    # solution = minimize(objective,x,method='trust-constr',bounds=bounds,constraints=cons)
    # May need to consider using global minimization as the objective function is probably not convex

    # solution = shgo(objective, bounds=bounds, minimizer_kwargs={'method': 'SLSQP', 'bounds': bounds})

    # solution = dual_annealing(
    #     objective,
    #     bounds=bounds,
    #     x0=leaf_ingredients,
    #     maxiter=1000,
    #     # initial_temp=100,
    #     visit=1.5, # This was found by trial and error
    #     # no_local_search=True,
    #     minimizer_kwargs={"method": "SLSQP", "bounds": bounds},
    # )

    # solution = basinhopping(
    #     objective,
    #     x0=leaf_ingredients,
    #     minimizer_kwargs={"method": "SLSQP", "bounds": bounds},
    # )

    # Problem with: fr-1000-some-specified-popular/5038862134729.json
    solution = differential_evolution(
        objective,
        bounds,
        args=args,
        x0=x0,
        polish=False, # Don't polish results to help with performance
        rng=0, # Seed random number generator so we get consistent results between tests
        workers=-1 if len(leaf_ingredients) > 10 else 1, # Gives a bit of an improvement with more complex products but not worth it for simple ones
        updating='deferred', # Need to set this if we are going to set workers
        # popsize=100, # Default is 15. Increasing this really slows things down
        # init='sobol', # Changing this didn't seem to make much difference
        tol=0.001, # Needed a lower value here to pass tests. Didn't seem to affect performance much
        atol=1, # Going higher than 1 seems to break tests
        # mutation=(1.5, 1.9), # Tried increasing this but gave poor results
        recombination=0.89 # Higher values seem to improve performance. This was highest I could go and still pass tests
    )

    # # DIRECT algorithm seems to cope best with our non-linear objective functions and the potentially large number of local minima
    # # It also gives consistent results where other algorithms use randomization a lot which gives different results from one run to the next
    # # For details of arguments see: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.direct.html
    # solution = direct(
    #     objective,
    #     bounds,
    #     args=[penalties],
    #     eps=0.01,  # Bit of trial and error here but going too much higher seems to find the wrong local minimum
    #     locally_biased=False,  # False is recommended for problems with lots of local minima. True passes tests but is less good for real life recipes
    #     f_min=0,  # Global minimum. Our objective function will never go negative
    #     #f_min_rtol=0.1, # Changing this didn't seem to make a lot of difference
    #     #len_tol=0.00001,  # If this is too small then the number of iterations will be exceeded, but too large gives inaccurate results
    #     #vol_tol=1e-32,
    #     # Following two give a trade-off between performance and accuracy. Have much more of an impact on performance if locally_biased is False
    #     maxfun=10000 * len(leaf_ingredients),
    #     maxiter=MAXITER,
    # )

    total_quantity = sum(solution.x)

    def set_percentages(ingredients):
        total_percent = 0
        for ingredient in ingredients:
            if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
                percent_estimate = set_percentages(ingredient["ingredients"])
            else:
                index = ingredient["index"]
                ingredient["quantity_estimate"] = round(solution.x[index], 2)
                # ingredient["lost_water"] = round(solution.x[index + 1], 2)
                percent_estimate = round(100 * solution.x[index] / total_quantity, 2)

            ingredient["percent_estimate"] = percent_estimate
            total_percent += percent_estimate

        return total_percent

    set_percentages(product["ingredients"])
    recipe_estimator = product["recipe_estimator"]
    recipe_estimator["status"] = 0
    recipe_estimator["status_message"] = solution.message
    # Note that for some algorithms penalties won't be set to the value from the best solution, so call the objective function again to get it
    objective(solution.x, *args)
    recipe_estimator['penalties'] = args[0]
    recipe_estimator["time"] = round(time.perf_counter() - current, 2)
    message = f"Product: {product.get('code')}, time: {recipe_estimator['time']} s, status: {solution.get('message')}, iterations: {solution.get('nit')}"
    if solution.success and solution.get("nit", 0) < MAXITER:
        print(message)
    else:
        warnings.warn(message)

    return solution
