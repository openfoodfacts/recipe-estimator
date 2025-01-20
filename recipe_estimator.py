import time  
from scipy.optimize import minimize
from ortools.sat.python import cp_model

from prepare_nutrients import prepare_nutrients

precision = 0.01
sf = 1000

def add_ingredients_to_solver(ingredients, model: cp_model.CpModel, total_ingredients, ingredient_numvars):
    for i,ingredient in enumerate(ingredients):

        ingredient_numvar = {'ingredient': ingredient, 'numvar': model.new_int_var(0, sf, 'ingredient')}
        ingredient_numvars.append(ingredient_numvar)
        # TODO: Known percentage or stated range

        if ('ingredients' in ingredient):
            # Child ingredients
            child_numvars = []
            total_ingredients += add_ingredients_to_solver(ingredient['ingredients'], model, total_ingredients, child_numvars)

            ingredient_numvar['child_numvars'] = child_numvars

        else:
            # Constrain water loss. If ingredient is 20% water then
            # raw ingredient - lost water must be greater than 80
            # ingredient - water_loss >= ingredient * (100 - water_ratio) / 100
            # ingredient - water_loss >= ingredient - ingredient * water ratio / 100
            # ingredient * water ratio / 100 - water_loss >= 0
            
            ingredient_numvar['lost_water'] = model.new_int_var(0, sf, 'lost_water')
            water = ingredient['nutrients'].get('water', {})
            maximum_water_content = water.get('percent_max', 0)

            water_loss_ratio_constraint = model.add_linear_constraint((ingredient_numvar['numvar'] * 0.01 * maximum_water_content) - ingredient_numvar['lost_water'], 0, sf)

            total_ingredients += ingredient_numvar['numvar'] * sf
            total_ingredients += -1.0 * ingredient_numvar['lost_water'] * sf

    return total_ingredients

# Add constraints to ensure that the quantity of each ingredient is greater than or equal to the quantity of the next ingredient
# and that the sum of children ingredients is equal to the parent ingredient
def add_relative_constraints_on_ingredients(model: cp_model.CpModel, parent_ingredient_numvar, ingredient_numvars):

    # Constraint: parent_ingredient = sum(children_ingredients)
    if (parent_ingredient_numvar is not None):
        parent_ingredient_constraint = model.add_linear_constraint(lb = 0,ub = 0)
        parent_ingredient_constraint.set_coefficient(parent_ingredient_numvar['numvar'], 1 * sf)
        print("parent_ingredient_constraint - parent :", parent_ingredient_constraint.name(), parent_ingredient_numvar['ingredient']['id'])
        for i,ingredient_numvar in enumerate(ingredient_numvars):
            parent_ingredient_constraint.set_coefficient(ingredient_numvar['numvar'], -1 * sf)
            print("parent_ingredient_constraint - child :", parent_ingredient_constraint.name(), ingredient_numvar['ingredient']['id'])

    for i,ingredient_numvar in enumerate(ingredient_numvars):

        # Relative constraints on consecutive ingredients        
        if i < (len(ingredient_numvars) - 1):
            # constraint: ingredient (i) - ingredient (i+1) >= 0
            relative_constraint = model.add_linear_constraint(lb = 0)
            relative_constraint.set_coefficient(ingredient_numvar['numvar'], 1.0 * sf)
            relative_constraint.set_coefficient(ingredient_numvars[i+1]['numvar'], -1.0 * sf)
            print("relative_constraint:", relative_constraint.name, ingredient_numvar['ingredient']['id'], '>=', ingredient_numvars[i+1]['ingredient']['id'])
        
        # Recursively apply parent ingredient constraint and relative constraints to child ingredients
        if 'child_numvars' in ingredient_numvar:
            add_relative_constraints_on_ingredients(model, ingredient_numvar, ingredient_numvar['child_numvars'])

def add_to_relative_constraint(solver, relative_constraint, ingredient_numvar, coefficient):
    if 'child_numvars' in ingredient_numvar:
        child_numvars = ingredient_numvar['child_numvars']
        for i,child_numvar in enumerate(child_numvars):
            add_to_relative_constraint(solver, relative_constraint, child_numvar, coefficient)
            if i < (len(child_numvars) - 1):
                child_constraint = solver.Constraint(0, solver.infinity())
                add_to_relative_constraint(solver, child_constraint, child_numvar, 1.0)
                add_to_relative_constraint(solver, child_constraint, child_numvars[i+1], -1.0)
    else:
        print("relative_constraint:", relative_constraint.name(), ingredient_numvar['ingredient']['id'], coefficient)
        relative_constraint.set_coefficient(ingredient_numvar['numvar'], coefficient * sf)

# For each ingredient, get the quantity estimate from the solver (for leaf ingredients)
# or sum the quantity estimates of the child ingredients (for non-leaf ingredients)
def get_quantity_estimate(ingredient_numvars):
    total_quantity = 0
    quantity_estimate = 0
    for ingredient_numvar in ingredient_numvars:
        if ('child_numvars' in ingredient_numvar):
            quantity_estimate = get_quantity_estimate(ingredient_numvar['child_numvars'])
        else:
            quantity_estimate = ingredient_numvar['numvar'].solution_value() / sf
            ingredient_numvar['ingredient']['lost_water'] = ingredient_numvar['lost_water'].solution_value() / sf
        
        ingredient_numvar['ingredient']['quantity_estimate'] = quantity_estimate
        total_quantity += quantity_estimate

    return total_quantity


def set_percent_estimate(ingredients, total_quantity):
    for ingredient in ingredients:
        if ('ingredients' in ingredient):
            set_percent_estimate(ingredient['ingredients'], total_quantity)

        ingredient['percent_estimate'] = 100 * ingredient['quantity_estimate'] / total_quantity


def add_ingredient_nutrients(ingredient_numvars, nutrient_key, nutrient_total_from_ingredients):
    for ingredient_numvar in ingredient_numvars:
        ingredient = ingredient_numvar['ingredient']
        if 'child_numvars' in ingredient_numvar:
            #print(ingredient['indent'] + ' - ' + ingredient['text'] + ':')
            nutrient_total_from_ingredients += add_ingredient_nutrients(ingredient_numvar['child_numvars'], nutrient_key, nutrient_total_from_ingredients)
        else:
            # TODO: Figure out whether to do anything special with < ...
            ingredient_nutrient =  ingredient['nutrients'][nutrient_key]
            #print(ingredient['indent'] + ' - ' + ingredient['text'] + ' (' + ingredient['ciqual_code'] + ') : ' + str(ingredient_nutrient))
            print("nutrient_distance:", ingredient['id'], nutrient_key, ingredient_nutrient['percent_min'], ingredient_nutrient['percent_max'])
            nutrient_total_from_ingredients += (ingredient_numvar['numvar'] * (ingredient_nutrient['percent_min'] / 100) * sf)

    return nutrient_total_from_ingredients

# Add an objective to minimize the difference between the quantity of each ingredient and the next ingredient (and 0 for the last ingredient)
def add_objective_to_minimize_maximum_distance_between_ingredients(solver, objective, weighting, ingredient_numvars):
    
    max_ingredients_distance = solver.NumVar(0, solver.infinity(), "max_ingredients_distance")

    for i,ingredient_numvar in enumerate(ingredient_numvars):
        
        # constraint: ingredient(i) - ingredient(i+1) <= max_ingredients_distance
        # can be expressed as: ingredient(i) - ingredient(i+1) - max_ingredients_distance <= 0
        constraint = solver.Constraint(-solver.infinity(), 0)
        constraint.SetCoefficient(ingredient_numvar['numvar'], 1)
        if i < (len(ingredient_numvars) - 1):
            constraint.SetCoefficient(ingredient_numvars[i+1]['numvar'], -1)
            # for the last ingredient, we look at its distance to 0
            # so the constraint is only ingredient(i) < max_ingredients_distance
            # and we don't need add it to the constraint
        constraint.SetCoefficient(max_ingredients_distance, -1)

        # Apply recursively to child ingredients
        if 'child_numvars' in ingredient_numvar:
            add_objective_to_minimize_maximum_distance_between_ingredients(solver, objective, weighting, ingredient_numvar['child_numvars'])

    objective.SetCoefficient(max_ingredients_distance, weighting)

def water_constraint(i, maximum_water_content):
    return { 'type': 'ineq', 'fun': lambda x: x[i * 2] * maximum_water_content * 0.01 - x[i * 2 + 1]}

def ingredient_order_constraint(i):
    return { 'type': 'ineq', 'fun': lambda x: x[i * 2 - 2] - x[i * 2]}

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
    for i,ingredient in enumerate(ingredients):
        x.append(100 / len(ingredients))
        bounds.append(bound)
        x.append(0)
        bounds.append(bound)

        # Set lost water constraint
        water = ingredient['nutrients'].get('water', {})
        maximum_water_content = water.get('percent_max', 0)
        cons.append(water_constraint(i, maximum_water_content))

        # Set order constraint
        if (i > 0):
            cons.append(ingredient_order_constraint(i))

    def total_ingredients(x):
        return sum(x[0::2]) - sum(x[1::2]) - 100
    cons.append({ 'type': 'eq', 'fun': total_ingredients})

    # def objective(x):
    #     return (10 - (x[0] * 0.15 + x[2] * 0.03)) ** 2

    def objective(x):
        nutrient_difference = 0

        for nutrient_key in nutrients:
            nutrient = nutrients[nutrient_key]

            weighting = nutrient.get('weighting')
            # Skip nutrients that don't have a weighting
            if weighting is None or weighting == 0:
                #print("Skipping nutrient without weight:", nutrient_key)
                continue

            nutrient_total = nutrient['product_total']
            nutrient_total_from_ingredients = 0
            for i,ingredient in enumerate(ingredients):
                ingredient_nutrient =  ingredient['nutrients'][nutrient_key]
                nutrient_total_from_ingredients += x[i * 2] * (ingredient_nutrient['percent_min'] / 100)

            nutrient_difference += (nutrient_total - nutrient_total_from_ingredients) ** 2

        return nutrient_difference

    solution = minimize(objective,x,method='COBYQA',bounds=bounds,constraints=cons)

    total_quantity = sum(solution.x[0::2])
    for i,ingredient in enumerate(ingredients):
        ingredient['quantity_estimate'] = solution.x[i * 2]
        ingredient['lost_water'] = solution.x[i * 2 + 1]
        ingredient['percent_estimate'] = 100 * solution.x[i * 2] / total_quantity

    end = time.perf_counter()
    recipe_estimator['time'] = end - current
    recipe_estimator['status'] = 0
    #recipe_estimator['iterations'] = solver.iterations()

    print('Time spent in solver: ', recipe_estimator['time'], 'seconds')

    return solution
