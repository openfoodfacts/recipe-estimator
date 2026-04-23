import math
import time
import cvxpy as cp
import numpy as np

from .fitness import get_objective_function_args, objective as objective_function

from .prepare_nutrients import prepare_nutrients

def add_ingredient_order_constraints(ingredients, constraints, leaf_ingredients, ingredient_percentages, water_percentages):
    previous_ingredients = None
    total_ingredients = []
    for ingredient in ingredients:
        if ('ingredients' in ingredient and len(ingredient['ingredients']) > 0):
            # Child ingredients
            my_ingredients = add_ingredient_order_constraints(ingredient['ingredients'], constraints, leaf_ingredients, ingredient_percentages, water_percentages)
        else:
            my_ingredients = [ingredient_percentages[len(leaf_ingredients)]]
            leaf_ingredients.append(ingredient)
            water_percentages.append(ingredient['nutrients'].get('water', {}).get('percent_nom', 0) * 0.01)
            
        if previous_ingredients and my_ingredients:
            constraints.append(sum(previous_ingredients) >= sum(my_ingredients))

        total_ingredients.extend(my_ingredients)
        previous_ingredients = my_ingredients
    
    return total_ingredients

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
    add_ingredient_order_constraints(ingredients, constraints, leaf_ingredients, ingredient_percentages, water_percentages)

    # Hard constraint: sum of ingredients less maximum water loss can't be greater than 100g
    constraints.append(cp.sum(ingredient_percentages) - (ingredient_percentages @ water_percentages) <= 100)

    for nutrient_key in nutrients:
        nutrient = nutrients[nutrient_key]

        # We square root the weighting as it gets squared again later when the variances are calculated
        weighting = math.sqrt(nutrient.get('weighting', 0))
        # Skip nutrients that don't have a weighting
        if weighting == 0:
            continue
        
        product_nutrients.append(nutrient['product_total'] * weighting)
        ingredient_nutrients = []
        
        for i, ingredient in enumerate(leaf_ingredients):
            ingredient_nutrient_percent =  ingredient['nutrients'].get(nutrient_key, {}).get('percent_nom', 0)
            ingredient_nutrients.append(ingredient_nutrient_percent * 0.01 * weighting)

        ingredients_nutrients.append(ingredient_nutrients)


    A = np.array(ingredients_nutrients)
    b = np.array(product_nutrients)
    # Use an objective to get the ingredients to add up to close to 100g,
    # which effectively adds a cost for evaporation.
    # Could potentially adjust the weighting here depending on the food category
    EVAPORATION_COST = 0.01
    objective = cp.Minimize(cp.sum_squares(A @ ingredient_percentages - b) + EVAPORATION_COST * cp.square(sum(ingredient_percentages) - 100))
    prob = cp.Problem(objective, constraints)
    prob.solve()

    solution_x = ingredient_percentages.value
    product_total_quantity = sum(solution_x)

    for i, ingredient in enumerate(leaf_ingredients):
        ingredient["percent_estimate"] = round(100 * solution_x[i] / product_total_quantity, 2)
        ingredient["quantity_estimate"] = round(solution_x[i], 2)

    # Calculate objective function so we can compare with SciPy
    quantities = np.array([float(ingredient['quantity_estimate']) for ingredient in leaf_ingredients])
    [_, _, args] = get_objective_function_args(product)
    objective_function(quantities, *args)
    recipe_estimator['penalties'] = args[0]
    recipe_estimator["status"] = 0
    recipe_estimator["status_message"] = prob.status
    recipe_estimator["time"] = round(time.perf_counter() - current, 2)

    return