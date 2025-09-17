import time
import warnings
import numpy
from scipy.optimize import nnls


from .fitness import get_objective_function_args, objective, NUTRIENT_WITHIN_BOUNDS_PENALTY, TOTAL_MASS_MORE_THAN_100_PENALTY

def estimate_recipe(product):
    current = time.perf_counter()
    [bounds, leaf_ingredients, args] = get_objective_function_args(product)
    recipe_estimator = product['recipe_estimator']
    nutrients = {nutrient_key: nutrient for nutrient_key, nutrient in recipe_estimator['nutrients'].items() if nutrient['weighting'] > 0}
    num_ingredients = len(leaf_ingredients)
    num_nutrients = len(nutrients)
    
    # For NNLS each solution vector is the difference between this ingredient and the next lowest one
    # which allows us to enforce the order of ingredients.
    # Therefore when we create the coefficient array we need to include the quantity of all later ingredients
    # when calculating the nutrients for the current ingredient
    
    # Commented code also adds an extra vector to make the ingredients add up to 100%
    # A = numpy.zeros((num_nutrients + 1, num_ingredients))
    # b = [nutrient['product_total'] * NUTRIENT_WITHIN_BOUNDS_PENALTY for nutrient in nutrients.values()] + [TOTAL_MASS_MORE_THAN_100_PENALTY]
    A = numpy.zeros((num_nutrients, num_ingredients))
    b = [nutrient['product_total'] for nutrient in nutrients.values()]
    for i in range(num_ingredients):
        for n, nutrient_key in enumerate(nutrients.keys()):
            A[n,i] = sum([ingredient['nutrients'].get(nutrient_key, {}).get('percent_nom', 0) for ingredient in leaf_ingredients[0:i + 1]]) # * NUTRIENT_WITHIN_BOUNDS_PENALTY
        # Add extra coefficient to make things add up to 100%, but for the lower ingredients we need to factor
        # that this will be included in the total for all of the earlier ingredients
        # A[num_nutrients, i] = (i + 1) * TOTAL_MASS_MORE_THAN_100_PENALTY

    (solution, rnorm) = nnls(A, b)
    solution_x = numpy.array([100 * solution[i:num_ingredients].sum() for i in range(num_ingredients)])
    product_total_quantity = sum(solution_x)

    def set_percentages(ingredients):
        total_percent = 0
        total_quantity = 0
        for ingredient in ingredients:
            if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
                percent_estimate, quantity_estimate = set_percentages(ingredient["ingredients"])
            else:
                index = ingredient["index"]
                quantity_estimate = round(solution_x[index], 2)
                # ingredient["lost_water"] = round(solution.x[index + 1], 2)
                percent_estimate = round(100 * solution_x[index] / product_total_quantity, 2)

            ingredient["percent_estimate"] = percent_estimate
            ingredient["quantity_estimate"] = quantity_estimate
            total_percent += percent_estimate
            total_quantity += quantity_estimate

        return total_percent, total_quantity

    set_percentages(product["ingredients"])
    recipe_estimator["status"] = 0
    recipe_estimator["status_message"] = f"rnorm: {rnorm}"

    objective(solution_x, *args)
    recipe_estimator['penalties'] = args[0]
    recipe_estimator["time"] = round(time.perf_counter() - current, 2)
    message = f"Product: {product.get('code')}, time: {recipe_estimator['time']} s, rnorm: {rnorm}"
    print(message)

    return solution
