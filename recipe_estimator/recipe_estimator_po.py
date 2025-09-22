import time
import numpy


from .fitness import get_objective_function_args, objective

POWER = -1.0
def estimate_percentages(ingredients, percent_remaining = 100, current_max = 100, current_min = 100):
    # This is an implementation of the current PO algorithm.
    # First the min and max ranges are set.
    # For any ingredient the max can't be such that it could be bigger than an early ingredient,
    # e.g. ingredient 4 cannot be more than 25% as otherwise one of the earlier ingredients would have to be less than 25%
    # So max = 100 / ingredient position
    # The minimum only really applies to the first ingredient which can't be less than 100 / number of ingredients
    # e.g. for a 4 ingredient product the minimum for ingredient 1 is 25% as if it was lower the others can't bring the total up to 100%
    
    # For sub-ingredients the same applies, but the max = max of parent / ingredient position within parent
    # If the sub-ingredients are for the first ingredient then the minimum of the first sub-ingredient
    # will be the minimum of the parent ingredient / number of sub-ingredients
    
    # Once the min and max values are known the percentage estimate of the first ingredient is set to the mid point of its min and max
    # For subsequent ingredients the percentage is also the mid point but the max is constrained by the percent left to allocate.

    num_ingredients = len(ingredients)
    if num_ingredients < 1:
        return

    for n, ingredient in enumerate(ingredients):
        this_max = current_max / (n + 1)
        this_min = 0
        if n == 0:
            this_min = current_min / num_ingredients

        ingredient["percent_min"] = this_min
        ingredient["percent_max"] = this_max

        # Limit the max for the estimate to the percent remaining
        estimate_max = this_max if this_max < percent_remaining else percent_remaining
        estimate = (estimate_max + this_min) / 2
        if n == (num_ingredients - 1):
            estimate = percent_remaining
        
        ingredient["percent_estimate"] = estimate
        ingredient["quantity_estimate"] = estimate

        if "ingredients" in ingredient:
            estimate_percentages(ingredient["ingredients"], percent_remaining, this_max, this_min)

        percent_remaining -= estimate

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
