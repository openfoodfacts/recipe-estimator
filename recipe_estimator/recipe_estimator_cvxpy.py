import time
import cvxpy as cp
import numpy as np

from .fitness import get_objective_function_args, objective as objective_function

from .prepare_nutrients import prepare_nutrients

def add_ingredient_order_constraints(ingredients, constraints, leaf_ingredients, ingredient_variables):
    previous_ingredients = None
    total_ingredients = []
    for ingredient in ingredients:
        if ('ingredients' in ingredient and len(ingredient['ingredients']) > 0):
            # Child ingredients
            my_ingredients = add_ingredient_order_constraints(ingredient['ingredients'], constraints, leaf_ingredients, ingredient_variables)
        else:
            my_ingredients = [ingredient_variables[len(leaf_ingredients)]]
            leaf_ingredients.append(ingredient)
            
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
    x = cp.Variable(leaf_ingredient_count,nonneg=True)
    constraints = [cp.sum(x) == 100]
    leaf_ingredients = []
    add_ingredient_order_constraints(ingredients, constraints, leaf_ingredients, x)

    for nutrient_key in nutrients:
        nutrient = nutrients[nutrient_key]

        weighting = nutrient.get('weighting')
        # Skip nutrients that don't have a weighting
        if weighting is None or weighting == 0:
            print("Skipping nutrient without weight:", nutrient_key)
            continue
        
        product_nutrients.append(nutrient['product_total'])
        ingredient_nutrients = []
        
        for i, ingredient in enumerate(leaf_ingredients):
            ingredient_nutrient_percent =  ingredient['nutrients'].get(nutrient_key, {}).get('percent_nom', 0)
            ingredient_nutrients.append(ingredient_nutrient_percent * 0.01)

        ingredients_nutrients.append(ingredient_nutrients)


    A = np.array(ingredients_nutrients)
    b = np.array(product_nutrients)
    objective = cp.Minimize(cp.norm(A @ x - b, 2))
    prob = cp.Problem(objective, constraints)
    prob.solve()

    solution_x = x.value
    product_total_quantity = sum(solution_x)

    for i, ingredient in enumerate(leaf_ingredients):
        ingredient["percent_estimate"] = round(100 * solution_x[i] / product_total_quantity, 2)
        ingredient["quantity_estimate"] = round(solution_x[i], 2)

    # Calculate objective function so we can compare with SciPy
    quantities = np.array([float(ingredient['quantity_estimate']) for ingredient in leaf_ingredients])
    [_, _, args] = get_objective_function_args(product)
    objective_function(quantities, *args)
    recipe_estimator['penalties'] = args[0]

    return