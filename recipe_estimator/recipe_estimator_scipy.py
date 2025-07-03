import time
from scipy.optimize import minimize, LinearConstraint, shgo

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


# estimate_recipe() uses a linear solver to estimate the quantities of all leaf ingredients (ingredients that don't have child ingredient)
# The solver is used to minimise the difference between the sum of the nutrients in the leaf ingredients and the total nutrients in the product
def estimate_recipe(product):
    current = time.perf_counter()
    leaf_ingredient_count = prepare_nutrients(product)
    ingredients = product["ingredients"]
    recipe_estimator = product["recipe_estimator"]
    nutrients = recipe_estimator["nutrients"]

    # For the model we need an array of variables. This will be the quantity of each leaf ingredient to make 100g of product
    # in order followed by the amount of mass (typically water) lost during preparation (e.g. evaporation during cooking)
    # For example, a simple tomato sauce of tomatoes and onions might have a matrix of [120, 60, 50, 10]
    # This is saying we start with 120g of tomatoes and 50g of onions and during cooking we lose 60g water from the
    # tomatoes and 10g from the onions.
    # The constraints we apply are as follows:
    #  - Total of ingredients minus lost mass must add up to 100. Expressed as a matrix [1, -1, 1, -1] = 100
    #  - Lost mass cannot be greater that the water content of each item. So:
    #       Tomatoes with 80% water: [0.8, -1, 0, 0] >= 0
    #       Onions with 20% water:   [0, 0, 0.2, -1] >= 0
    # The later ingredient must be less than the one before. [1, 0, -1, 0] >= 0. For n ingredients there will be n-1 of these constraints
    # If we are dealing with an ingredient where the next ingredient has sub-ingredients then the earlier ingredient must be greater than
    # or equal to the the sum of the sub-ingredients of the later ingredient. Similarly if the earlier ingredient has sub-ingredients
    # then the sum of its sub-ingredients must be greater than or equal to the next ingredient.
    # For the objective function, for each nutrient we sum the product of the mass of each ingredient and its nutrient proportion
    # and assign a penalty based on its divergence from the nutrient value of the product. We weight this depending on a factor for the nutrient.

    # Leaf ingredients are those that do not have sub-ingredients. Each leaf ingredient is immediately followed by the mass lost (typically water)
    # for that ingredient during processing (e.g. cooking)
    leaf_ingredients = []
    ingredient_order_multipliers = []
    water_loss_multipliers = []
    maximum_percentages = []

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
        ingredient_multipliers = [0] * leaf_ingredient_count * 2
        for i in range(0, leaf_ingredient_count * 2, 2):
            if i >= start_of_previous_parent and i < leaf_ingredient_index:
                ingredient_multipliers[i] = 1
            if (
                i >= leaf_ingredient_index
                and i < leaf_ingredient_index + sub_ingredient_count * 2
            ):
                ingredient_multipliers[i] = -1
        return ingredient_multipliers

    # Prepare nutrients information in arrays for fast objective function
    nutrient_names = []
    product_nutrients = []
    # Following is an array of nutrients each containing an array of data for that nutrient for each ingredient (not including the lost water leaves)
    nutrient_ingredients = []
    nutrient_weightings = []
    nutrient_penalty_factors = []
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
        nutrient_penalty_factors.append(nutrient["penalty_factor"])

    def add_ingredients(total_percent, ingredients):
        leaf_ingredients_added = 0
        # Initial estimate of ingredients is a geometric progression where each is half the previous one
        # Sum of a  geometric progression is Sn = a(1 - r^n) / (1 - r)
        # In our case Sn = 100 and r = 0.5 so our first ingredient (a) will be
        # (100 * 0.5) / (1 - 0.5 ^ n)
        initial_estimate = (total_percent * 0.5) / (1 - 0.5 ** len(ingredients))
        for i, ingredient in enumerate(ingredients):
            leaf_ingredient_index = len(leaf_ingredients)

            if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
                sub_ingredient_count = add_ingredients(
                    initial_estimate, ingredient["ingredients"]
                )
            else:
                # Set lost water constraint
                water = ingredient["nutrients"].get("water", {})
                maximum_water_content = water.get("percent_nom", 0) * 0.01
                water_loss_multipliers.append(
                    water_constraint(leaf_ingredient_index, maximum_water_content)
                )

                # Initial estimate. 0.5 of previous ingredient
                leaf_ingredients.append(initial_estimate)
                maximum_weight = (
                    None
                    if maximum_water_content == 1
                    else 100 / (1 - maximum_water_content)
                )
                maximum_percentages.append(maximum_weight)

                # Water loss. Initial estimate is zero
                leaf_ingredients.append(0)
                maximum_percentages.append(None if maximum_water_content == 1 else maximum_water_content * maximum_weight)

                ingredient["index"] = leaf_ingredient_index
                sub_ingredient_count = 1

                for n, nutrient_key in enumerate(nutrient_names):
                    ingredient_nutrient = ingredient["nutrients"][nutrient_key]
                    nutrient_ingredients[n].append(
                        {
                            "nom": ingredient_nutrient["percent_nom"] / 100,
                            "min": ingredient_nutrient["percent_min"] / 100,
                            "max": ingredient_nutrient["percent_max"] / 100,
                        }
                    )

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

    add_ingredients(100, ingredients)

    # Total mass of all ingredients less all lost water must be 100g
    total_mass_multipliers = [0] * leaf_ingredient_count * 2
    for i in range(0, leaf_ingredient_count * 2):
        total_mass_multipliers[i] = -1 if i % 2 else 1

    def objective(ingredient_percentages):
        penalty = 0

        for n, nutrient_total in enumerate(product_nutrients):
            nom_nutrient_total_from_ingredients = 0
            min_nutrient_total_from_ingredients = 0
            max_nutrient_total_from_ingredients = 0
            for i, nutrient_ingredient in enumerate(nutrient_ingredients[n]):
                nom_nutrient_total_from_ingredients += (
                    ingredient_percentages[i * 2] * nutrient_ingredient["nom"]
                )
                min_nutrient_total_from_ingredients += (
                    ingredient_percentages[i * 2] * nutrient_ingredient["min"]
                )
                max_nutrient_total_from_ingredients += (
                    ingredient_percentages[i * 2] * nutrient_ingredient["max"]
                )

            # Factors need to quite large as the algorithms only make tiny changes to the variables to determine gradients
            # TODO: Need to experiment with factors here
            penalty += nutrient_weightings[n] * assign_penalty(
                nutrient_total,
                nom_nutrient_total_from_ingredients,
                100,
                min_nutrient_total_from_ingredients,
                max_nutrient_total_from_ingredients,
                1000 * nutrient_penalty_factors[n],
            )

        # Now add a penalty for the constraints and the bounds
        for multipliers in ingredient_order_multipliers:
            ingredient_order_test = sum([ingredient_quantity * multipliers[n] for n, ingredient_quantity in enumerate(ingredient_percentages)])
            # If the test is negative (ingredients bigger than previous) then add a big penalty
            if ingredient_order_test < 0:
                penalty += (-ingredient_order_test) * 10000

        for multipliers in water_loss_multipliers:
            water_loss_test = sum([ingredient_quantity * multipliers[n] for n, ingredient_quantity in enumerate(ingredient_percentages)])
            # If the test is negative (water loss is more than the expected maximum water content of the ingredient) then add a moderate penalty
            if water_loss_test < 0:
                penalty += (-water_loss_test) * 1000

        total_mass = 0
        for n, factor in enumerate(total_mass_multipliers):
            total_mass += ingredient_percentages[n] * factor
        # Add a high penalty as the total mass diverges from 100g
        penalty += abs(100 - total_mass) * 10000
        
        # Although we could also model bounds using penalties the optimizers seem to work better if they have bounds
        
        # for n, maximum_percentage in enumerate(maximum_percentages):
        #     if ingredient_percentages[n] < 0:
        #         # Add a big penalty for negative ingredients
        #         penalty += (-ingredient_percentages[n]) * 100000
        #     if maximum_percentage and ingredient_percentages[n] > maximum_percentage:
        #         # Add a moderate penalty if an ingredient is bigger than what we think it's maximum should be
        #         penalty += (ingredient_percentages[n] - maximum_percentage) * 1000

        return penalty

    # constraints = [
    #     LinearConstraint(A, lb=0)
    #     for A in ingredient_order_multipliers + water_loss_multipliers
    # ]
    # # For COBYLA can't use eq constraint
    # constraints.append(LinearConstraint(total_mass_multipliers, lb=99.99, ub=100.01))

    bounds = [[0, maximum_percentage] for maximum_percentage in maximum_percentages]

    # COBYQA is very slow
    # solution = minimize(objective,x,method='COBYLA',bounds=bounds,constraints=cons,options={'maxiter': 10000})
    solution = minimize(
        objective,
        leaf_ingredients,
        method="SLSQP",
        bounds=bounds,
        # constraints=constraints,
    )  # Fastest
    # solution = minimize(objective,x,method='trust-constr',bounds=bounds,constraints=cons)
    # May need to consider using global minimization as the objective function is probably not convex
    # Looks like shgo is the only one that supports constraints
    # solution = shgo(objective, bounds=bounds, constraints=cons) #, n = 1000, minimizer_kwargs={'method': 'COBYLA'})

    total_quantity = sum(solution.x[0::2])

    def set_percentages(ingredients):
        total_percent = 0
        for ingredient in ingredients:
            if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
                percent_estimate = set_percentages(ingredient["ingredients"])
            else:
                index = ingredient["index"]
                ingredient["quantity_estimate"] = round(solution.x[index], 2)
                ingredient["lost_water"] = round(solution.x[index + 1], 2)
                percent_estimate = round(100 * solution.x[index] / total_quantity, 2)

            ingredient["percent_estimate"] = percent_estimate
            total_percent += percent_estimate

        return total_percent

    set_percentages(ingredients)
    end = time.perf_counter()
    recipe_estimator["time"] = round(end - current, 2)
    recipe_estimator["status"] = 0
    recipe_estimator["status_message"] = solution.message
    print(f"Product: {product['code']}, time: {recipe_estimator['time']} s, status: {solution.message}, iterations: {solution.nit}")

    return solution
