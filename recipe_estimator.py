import time  
from scipy.optimize import minimize

from prepare_nutrients import prepare_nutrients

def water_constraint(i, maximum_water_content):
    return { 'type': 'ineq', 'fun': lambda x: x[i * 2] * maximum_water_content * 0.01 - x[i * 2 + 1]}

def ingredient_order_constraint(previous_start, this_start, this_count):
    return { 'type': 'ineq', 'fun': lambda x: sum(x[previous_start : this_start : 2]) - sum(x[this_start : this_start + this_count * 2 : 2])}

# estimate_recipe() uses a linear solver to estimate the quantities of all leaf ingredients (ingredients that don't have child ingredient)
# The solver is used to minimise the difference between the sum of the nutrients in the leaf ingredients and the total nutrients in the product
def estimate_recipe(product):
    current = time.perf_counter()
    prepare_nutrients(product)
    ingredients = product['ingredients']
    recipe_estimator = product['recipe_estimator']
    nutrients = recipe_estimator['nutrients']
    
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
    # TODO: explain how it works for sub-ingredients
    # For the objective function, for each nutrient we sum the product of the mass of each ingredient and its nutrient proportion 
    # and subtract this from the quoted nutrient value of the product. We square this and weight it and then minimise the
    # sum of the weighted squares of the nutrient differences.

    # Total of leaf level ingredients must add up to at least 100
    x = []
    cons = []
    bound = (0, None)
    bounds = []

    # Prepare nutrients information in arrays for fast objective function
    nutrient_names = []
    product_nutrients = []
    ingredients_nutrients = []
    nutrient_weightings = []
    for nutrient_key in nutrients:
        nutrient = nutrients[nutrient_key]

        weighting = nutrient.get('weighting')

        # Skip nutrients that don't have a weighting
        if weighting is None or weighting == 0:
            #print("Skipping nutrient without weight:", nutrient_key)
            continue
        nutrient_names.append(nutrient_key)
        product_nutrients.append(nutrient['product_total'])
        nutrient_weightings.append(weighting)
        ingredients_nutrients.append([])


    def add_ingredients(total, ingredients):
        added = 0
        start = len(x)
        # Initial estimate of ingredients is a geometric progression where each is half the previous one
        # Sum of a  geometric progression is Sn = a(1 - r^n) / (1 - r)
        # In our case Sn = 100 and r = 0.5 so our first ingredient (a) will be
        # (100 * 0.5) / (1 - 0.5 ^ n)
        a = (total * 0.5) / (1 - 0.5 ** len(ingredients))
        for i,ingredient in enumerate(ingredients):
            this_start = start + i * 2

            if ('ingredients' in ingredient and len(ingredient['ingredients']) > 0):
                ingredients_added = add_ingredients(a, ingredient['ingredients'])
            else:
                # Initial estimate. 0.5 of previous ingredient
                x.append(a)
                a /= 2
                bounds.append(bound)
 
                # Water loss
                x.append(0)
                bounds.append(bound)

                # Set lost water constraint
                water = ingredient['nutrients'].get('water', {})
                maximum_water_content = water.get('percent_max', 0)
                cons.append(water_constraint(i, maximum_water_content))

                ingredient['index'] = this_start
                ingredients_added = 1

                for n,nutrient_key in enumerate(nutrient_names):
                    ingredient_nutrient =  ingredient['nutrients'][nutrient_key]
                    ingredients_nutrients[n].append(ingredient_nutrient['percent_min'] / 100)

            # Set order constraint
            if (i > 0):
                # Sum of children must be less than previous ingredient (or sum of its children)
                cons.append(ingredient_order_constraint(previous_start, this_start, ingredients_added))

            added += ingredients_added
            previous_start = this_start
        return added

    add_ingredients(100, ingredients)

    cons.append({ 'type': 'eq', 'fun': lambda x: sum(x[0::2]) - sum(x[1::2]) - 100})

    def objective(x):
        nutrient_difference = 0

        for n, nutrient_total in enumerate(product_nutrients):
            nutrient_total_from_ingredients = 0
            for i, ingredient_nutrient in enumerate(ingredients_nutrients[n]):
                nutrient_total_from_ingredients += x[i * 2] * ingredient_nutrient

            nutrient_difference += nutrient_weightings[n] * (nutrient_total - nutrient_total_from_ingredients) ** 2

        return nutrient_difference

    solution = minimize(objective,x,method='SLSQP',bounds=bounds,constraints=cons)

    total_quantity = sum(solution.x[0::2])

    def set_percentages(ingredients):
        for ingredient in ingredients:
            if ('ingredients' in ingredient):
                set_percentages(ingredient['ingredients'])
            else:
                index = ingredient['index']
                ingredient['quantity_estimate'] = solution.x[index]
                ingredient['lost_water'] = solution.x[index + 1]
                ingredient['percent_estimate'] = 100 * solution.x[index] / total_quantity

    set_percentages(ingredients)
    end = time.perf_counter()
    recipe_estimator['time'] = end - current
    recipe_estimator['status'] = solution.status
    recipe_estimator['iterations'] = solution.nit

    print('Time spent in solver: ', recipe_estimator['time'], 'seconds')

    return solution
