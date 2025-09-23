import time
import numpy


from .fitness import get_objective_function_args, objective

FIRST_INGREDIENT = -0.43
SUBSEQUENT_POWER = -1.28
def estimate_percentages(ingredients, total = 100.0):
    # Each ingredient quantity = a * n ^ p
    # where p is the POWER constant, n is the ingredient number and a is the percentage of the first ingredient
    # We work out a by adding up all the results of the series with a = 1 and then factor a so that the total adds up to 100% (total)
    num_ingredients = len(ingredients)
    if num_ingredients < 1:
        return
    
    # First ingredient is 100 * n ^ -0.5
    first_ingredient = round(total * num_ingredients ** FIRST_INGREDIENT, 2)
    
    # We now have a remaining sum to allocate to the other ingredients
    if num_ingredients > 1:
        raw_sum = sum([(n + 2.0) ** SUBSEQUENT_POWER for n in range(num_ingredients - 1)])
        a = (total - first_ingredient) / raw_sum
    for n, ingredient in enumerate(ingredients):
        estimate = first_ingredient if n == 0 else round(a * (n + 1.0) ** SUBSEQUENT_POWER, 2)
        ingredient["percent_estimate"] = estimate
        ingredient["quantity_estimate"] = estimate
        if "ingredients" in ingredient:
            estimate_percentages(ingredient["ingredients"], estimate)
    return
    
    
def estimate_recipe(product):
    current = time.perf_counter()
    [bounds, leaf_ingredients, args] = get_objective_function_args(product)
    recipe_estimator = product['recipe_estimator']
    
    estimate_percentages(product["ingredients"])
    recipe_estimator["status"] = 0
    recipe_estimator["status_message"] = f"OK"

    solution_x = numpy.array([ingredient['quantity_estimate'] for ingredient in leaf_ingredients])
    objective(solution_x, *args)
    recipe_estimator['penalties'] = args[0]
    recipe_estimator["time"] = round(time.perf_counter() - current, 2)
    message = f"Product: {product.get('code')}, time: {recipe_estimator['time']} s"
    print(message)

    return
