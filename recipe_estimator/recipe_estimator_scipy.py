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
def assign_penalty(value, nom_value, tolerance_penalty, min_value, max_value, steep_gradient):
    if (value < min_value):
        return tolerance_penalty + (min_value - value) * steep_gradient

    if (value > max_value):
        return tolerance_penalty + (value - max_value) * steep_gradient

    if (value > nom_value):
        return tolerance_penalty * (value - nom_value) / (max_value - nom_value)
    
    if (value < nom_value):
        return tolerance_penalty * (nom_value - value) / (nom_value - min_value)
    
    # Value = nom_value
    return 0

# estimate_recipe() uses a linear solver to estimate the quantities of all leaf ingredients (ingredients that don't have child ingredient)
# The solver is used to minimise the difference between the sum of the nutrients in the leaf ingredients and the total nutrients in the product
def estimate_recipe(product):
    current = time.perf_counter()
    leaf_ingredient_count = prepare_nutrients(product)
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
    bounds = []

    def water_constraint(i, maximum_water_content):
        # return { 'type': 'ineq', 'fun': lambda x: x[i] * maximum_water_content - x[i + 1]}
        A = [0] * leaf_ingredient_count * 2
        A[i] = maximum_water_content
        A[i + 1] = -1
        return LinearConstraint(A, lb = 0)

    def ingredient_order_constraint(previous_start, this_start, this_count):
        # return { 'type': 'ineq', 'fun': lambda x: sum(x[previous_start : this_start : 2]) - sum(x[this_start : this_start + this_count * 2 : 2])}
        A = [0] * leaf_ingredient_count * 2
        for i in range(0, leaf_ingredient_count * 2, 2):
            if i >= previous_start and i < this_start:
                A[i] = 1
            if i >= this_start and i < this_start + this_count * 2:
                A[i] = -1
        return LinearConstraint(A, lb = 0)

    # Prepare nutrients information in arrays for fast objective function
    nutrient_names = []
    product_nutrients = []
    ingredients_nutrients = []
    nutrient_weightings = []
    nutrient_penalty_factors = []
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
        nutrient_penalty_factors.append(nutrient['penalty_factor'])


    def add_ingredients(total, ingredients):
        added = 0
        # Initial estimate of ingredients is a geometric progression where each is half the previous one
        # Sum of a  geometric progression is Sn = a(1 - r^n) / (1 - r)
        # In our case Sn = 100 and r = 0.5 so our first ingredient (a) will be
        # (100 * 0.5) / (1 - 0.5 ^ n)
        a = (total * 0.5) / (1 - 0.5 ** len(ingredients))
        for i,ingredient in enumerate(ingredients):
            this_start = len(x)

            if ('ingredients' in ingredient and len(ingredient['ingredients']) > 0):
                ingredients_added = add_ingredients(a, ingredient['ingredients'])
            else:
                # Set lost water constraint
                water = ingredient['nutrients'].get('water', {})
                maximum_water_content = water.get('percent_nom', 0) * 0.01
                cons.append(water_constraint(this_start, maximum_water_content))

                # Initial estimate. 0.5 of previous ingredient
                x.append(a)
                maximum_weight = None if maximum_water_content == 1 else 100 / (1 - maximum_water_content)
                bounds.append((0, maximum_weight))
 
                # Water loss
                x.append(0)
                bounds.append((0, None if maximum_water_content == 1 else maximum_water_content * maximum_weight))

                ingredient['index'] = this_start
                ingredients_added = 1

                for n,nutrient_key in enumerate(nutrient_names):
                    ingredient_nutrient =  ingredient['nutrients'][nutrient_key]
                    ingredients_nutrients[n].append({
                        'nom': ingredient_nutrient['percent_nom'] / 100,
                        'min': ingredient_nutrient['percent_min'] / 100,
                        'max': ingredient_nutrient['percent_max'] / 100,
                    })

            # Set order constraint
            if (i > 0):
                # Sum of children must be less than previous ingredient (or sum of its children)
                cons.append(ingredient_order_constraint(previous_start, this_start, ingredients_added))

            a /= 2
            added += ingredients_added
            previous_start = this_start
        return added

    add_ingredients(100, ingredients)

    def objective(x):
        penalty = 0

        for n, nutrient_total in enumerate(product_nutrients):
            nom_nutrient_total_from_ingredients = 0
            min_nutrient_total_from_ingredients = 0
            max_nutrient_total_from_ingredients = 0
            for i, ingredient_nutrient in enumerate(ingredients_nutrients[n]):
                nom_nutrient_total_from_ingredients += x[i * 2] * ingredient_nutrient['nom']
                min_nutrient_total_from_ingredients += x[i * 2] * ingredient_nutrient['min']
                max_nutrient_total_from_ingredients += x[i * 2] * ingredient_nutrient['max']

            # Factors need to quite large as the algorithms only make tiny changes to the variables to determine gradients
            # TODO: Need to experiment with factors here
            penalty += nutrient_weightings[n] * assign_penalty(nutrient_total, 
                                                               nom_nutrient_total_from_ingredients, 100,
                                                                min_nutrient_total_from_ingredients,
                                                                 max_nutrient_total_from_ingredients, 1000 * nutrient_penalty_factors[n])
        return penalty

    # For COBYLA can't use eq constraint
    A = [0] * leaf_ingredient_count * 2
    for i in range(0, leaf_ingredient_count * 2):
        A[i] = -1 if i % 2 else 1
    cons.append(LinearConstraint(A, lb = 99.99, ub = 100.01))
    # cons.append({ 'type': 'ineq', 'fun': lambda x: sum(x[0::2]) - sum(x[1::2]) - 99.99})
    # cons.append({ 'type': 'ineq', 'fun': lambda x: 100.01 - (sum(x[0::2]) - sum(x[1::2]))})

    # COBYQA is very slow
    #solution = minimize(objective,x,method='COBYLA',bounds=bounds,constraints=cons,options={'maxiter': 10000})
    solution = minimize(objective,x,method='SLSQP',bounds=bounds,constraints=cons) # Fastest
    #solution = minimize(objective,x,method='trust-constr',bounds=bounds,constraints=cons)
    # May need to consider using global minimization as the objective function is probably not convex
    # Looks like shgo is the only one that supports constraints
    # solution = shgo(objective, bounds=bounds, constraints=cons) #, n = 1000, minimizer_kwargs={'method': 'COBYLA'})

    total_quantity = sum(solution.x[0::2])

    def set_percentages(ingredients):
        total_percent = 0
        for ingredient in ingredients:
            if ('ingredients' in ingredient and len(ingredient['ingredients']) > 0):
                percent_estimate = set_percentages(ingredient['ingredients'])
            else:
                index = ingredient['index']
                ingredient['quantity_estimate'] = solution.x[index]
                ingredient['lost_water'] = solution.x[index + 1]
                percent_estimate = round(100 * solution.x[index] / total_quantity, 2)

            ingredient['percent_estimate'] = percent_estimate
            total_percent += percent_estimate

        return total_percent

    set_percentages(ingredients)
    end = time.perf_counter()
    recipe_estimator['time'] = end - current
    recipe_estimator['status'] = 0
    recipe_estimator['status_message'] = solution.message
    if solution.status != 0:
        print(f"Product: {product['code']}, status: {solution.message}, iterations: {solution.nit}")
    #recipe_estimator['iterations'] = solution.nit

    print('Time spent in solver: ', recipe_estimator['time'], 'seconds')

    return solution
