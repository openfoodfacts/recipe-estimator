import math
import time
import cvxpy as cp
import numpy as np

from .fitness import get_objective_function_args, objective as objective_function

from .prepare_nutrients import prepare_nutrients

POWER = -1.7
EVAPORATION_COST = 0.01
UNKNOWN_INGREDIENT_WEIGHTING = 0.002


def add_ingredient_order_constraints(
    ingredients,
    constraints,
    leaf_ingredients,
    ingredient_percentages,
    water_percentages,
):
    previous_ingredients = None
    total_ingredients = []
    for ingredient in ingredients:
        if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
            # Child ingredients
            my_ingredients = add_ingredient_order_constraints(
                ingredient["ingredients"],
                constraints,
                leaf_ingredients,
                ingredient_percentages,
                water_percentages,
            )
        else:
            my_ingredients = [ingredient_percentages[len(leaf_ingredients)]]
            leaf_ingredients.append(ingredient)
            # Tried defaulting to a nominal value for water for unknown ingredients
            # but didn't seem to help
            water_percentages.append(
                ingredient["nutrients"].get("water", {}).get("percent_nom", 0) * 0.01
            )

        if previous_ingredients and my_ingredients:
            constraints.append(sum(previous_ingredients) >= sum(my_ingredients))

        total_ingredients.extend(my_ingredients)
        previous_ingredients = my_ingredients

    return total_ingredients


def estimate_percentages(
    ingredient_percentages, objectives, ingredients, total=100.0, index=0, percent_unknown = 0
):
    # Each ingredient quantity = a * n ^ p
    # where p is the POWER constant, n is the ingredient number and a is the percentage of the first ingredient
    # We work out a by adding up all the results of the series with a = 1 and then factor a so that the total adds up to 100% (total)
    num_ingredients = len(ingredients)
    if num_ingredients < 1:
        return

    raw_sum = sum([(n + 1.0) ** POWER for n in range(num_ingredients)])
    a = total / raw_sum
    for n, ingredient in enumerate(ingredients):
        estimate = round(a * (n + 1.0) ** POWER, 2)

        if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
            index, percent_unknown = estimate_percentages(
                ingredient_percentages,
                objectives,
                ingredient["ingredients"],
                estimate,
                index,
                percent_unknown
            )
        else:
            # If ingredient has no nutrient information then add an objective to keep close to the estimate
            if len(ingredient["nutrients"]) == 0:
                percent_unknown += estimate
                objectives.append(
                    UNKNOWN_INGREDIENT_WEIGHTING
                    * cp.square(ingredient_percentages[index] - estimate)
                )
            index += 1

    return index, percent_unknown


def set_percentages(solution_x, ingredients, product_total_quantity, index=0):
    total_percent = 0
    total_quantity = 0
    for ingredient in ingredients:
        if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
            index, percent_estimate, quantity_estimate = set_percentages(
                solution_x, ingredient["ingredients"], product_total_quantity, index
            )
        else:
            quantity_estimate = round(solution_x[index], 2)
            percent_estimate = round(
                100 * solution_x[index] / product_total_quantity, 2
            )
            index += 1

        ingredient["percent_estimate"] = percent_estimate
        ingredient["quantity_estimate"] = quantity_estimate
        total_percent += percent_estimate
        total_quantity += quantity_estimate

    return index, total_percent, total_quantity


def get_nutrient_weighting(percent_unknown):
    # This curve is designed to give a weighting of 1 where all ingredients are known
    # 0.5 when 20% are unknown and
    # 0.01 when 50% are unknown
    # Down to zero when none are known
    return 1.053 / (1 + np.exp(0.152 * (percent_unknown - 19.33)))
    
    
def estimate_recipe(product):
    current = time.perf_counter()
    leaf_ingredient_count = prepare_nutrients(product, True)
    ingredients = product["ingredients"]
    recipe_estimator = product["recipe_estimator"]
    nutrients = recipe_estimator["nutrients"]

    ingredients_nutrients = []
    product_nutrients = []
    leaf_ingredients = []
    water_percentages = []

    ingredient_percentages = cp.Variable(leaf_ingredient_count, nonneg=True)
    constraints = []
    nutrient_weightings = []
    add_ingredient_order_constraints(
        ingredients,
        constraints,
        leaf_ingredients,
        ingredient_percentages,
        water_percentages,
    )

    # Hard constraint: sum of ingredients less maximum water loss can't be greater than 100g
    constraints.append(
        cp.sum(ingredient_percentages) - (ingredient_percentages @ water_percentages)
        <= 100
    )

    for nutrient_key in nutrients:
        nutrient = nutrients[nutrient_key]

        weighting = nutrient.get("weighting", 0)
        # Skip nutrients that don't have a weighting
        if weighting == 0:
            continue

        product_total = nutrient["product_total"]
        product_nutrients.append(product_total)
        nutrient_weightings.append(weighting)
        ingredient_nutrients = []

        for i, ingredient in enumerate(leaf_ingredients):
            ingredient_nutrient = ingredient["nutrients"].get(nutrient_key, {})
            ingredient_nutrient_percent = ingredient_nutrient.get("percent_nom", 0)
            ingredient_nutrients.append(ingredient_nutrient_percent * 0.01)

        ingredients_nutrients.append(ingredient_nutrients)
        
        # Tried adding a constraint that the minimum nutrient value for all ingredients can't exceed what is on the packaging
        # but it didn't improve the results
    
    objectives = []

    # Add objective to keep unknown ingredients close to the inverse power series
    _, percent_unknown = estimate_percentages(ingredient_percentages, objectives, ingredients)

    # Main objective to match ingredient nutrients to product nutrients
    if product_nutrients:
        ingredients_nutrients = np.array(ingredients_nutrients)
        nutrient_variance = cp.sum(nutrient_weightings @ cp.square(ingredients_nutrients @ ingredient_percentages - product_nutrients))
        # Reduce weighting if lots of ingredients are unknown
        nutrient_adjustment = 1 #get_nutrient_weighting(percent_unknown)
        objectives.append(nutrient_adjustment * nutrient_variance)


    # Get the ingredients to add up to close to 100g, which effectively adds a cost for evaporation.
    # Could potentially adjust the weighting here depending on the food category
    objectives.append(EVAPORATION_COST * cp.square(sum(ingredient_percentages) - 100))

    objective = cp.Minimize(sum(objectives))
    prob = cp.Problem(objective, constraints)
    prob.solve()

    solution_x = ingredient_percentages.value
    if product_nutrients:
        recipe_estimator["nutrient_variance"] = nutrient_variance.value.item()

    product_total_quantity = sum(solution_x)

    set_percentages(solution_x, ingredients, product_total_quantity)

    # Calculate objective function so we can compare with SciPy
    quantities = np.array(
        [float(ingredient["quantity_estimate"]) for ingredient in leaf_ingredients]
    )
    [_, _, args] = get_objective_function_args(product)
    objective_function(quantities, *args)
    recipe_estimator["penalties"] = args[0]
    recipe_estimator["status"] = 0
    recipe_estimator["status_message"] = prob.status
    recipe_estimator["time"] = round(time.perf_counter() - current, 2)

    return
