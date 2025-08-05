import time  
import numpy as np
from ortools.linear_solver import pywraplp

from .fitness import get_objective_function_args, objective as objective_function

from .prepare_nutrients import prepare_nutrients

precision = 0.01


def add_ingredients_to_solver(ingredients, solver, total_ingredients):
    ingredient_numvars = []

    for i,ingredient in enumerate(ingredients):

        ingredient_numvar = {'ingredient': ingredient, 'numvar': solver.NumVar(0.0, solver.infinity(), '')}
        ingredient_numvars.append(ingredient_numvar)
        # TODO: Known percentage or stated range

        if ingredient.get('ingredients'):
            # Child ingredients
            child_numvars = add_ingredients_to_solver(ingredient['ingredients'], solver, total_ingredients)

            ingredient_numvar['child_numvars'] = child_numvars

        else:
            # Constrain water loss. If ingredient is 20% water then
            # raw ingredient - lost water must be greater than 80
            # ingredient - water_loss >= ingredient * (100 - water_ratio) / 100
            # ingredient - water_loss >= ingredient - ingredient * water ratio / 100
            # ingredient * water ratio / 100 - water_loss >= 0
            
            ingredient_numvar['lost_water'] = solver.NumVar(0, solver.infinity(), '')
            water = ingredient['nutrients'].get('water', {})
            maximum_water_content = water.get('percent_nom', 0)
            print("maximum_water_content", ingredient['id'], maximum_water_content)

            water_loss_ratio_constraint = solver.Constraint(0, solver.infinity(),  '')
            water_loss_ratio_constraint.SetCoefficient(ingredient_numvar['numvar'], 0.01 * maximum_water_content)
            water_loss_ratio_constraint.SetCoefficient(ingredient_numvar['lost_water'], -1.0)

            total_ingredients.SetCoefficient(ingredient_numvar['numvar'], 1)
            total_ingredients.SetCoefficient(ingredient_numvar['lost_water'], -1.0)
            print("total_ingredients:", total_ingredients.name(), ingredient_numvar['ingredient']['id'])

    return ingredient_numvars

# Add constraints to ensure that the quantity of each ingredient is greater than or equal to the quantity of the next ingredient
# and that the sum of children ingredients is equal to the parent ingredient
def add_relative_constraints_on_ingredients(solver, parent_ingredient_numvar, ingredient_numvars):

    # Constraint: parent_ingredient = sum(children_ingredients)
    if (parent_ingredient_numvar is not None):
        parent_ingredient_constraint = solver.Constraint(0, 0)
        parent_ingredient_constraint.SetCoefficient(parent_ingredient_numvar['numvar'], 1)
        print("parent_ingredient_constraint - parent :", parent_ingredient_constraint.name(), parent_ingredient_numvar['ingredient']['id'])
        for i,ingredient_numvar in enumerate(ingredient_numvars):
            parent_ingredient_constraint.SetCoefficient(ingredient_numvar['numvar'], -1)
            print("parent_ingredient_constraint - child :", parent_ingredient_constraint.name(), ingredient_numvar['ingredient']['id'])

    for i,ingredient_numvar in enumerate(ingredient_numvars):

        # Relative constraints on consecutive ingredients        
        if i < (len(ingredient_numvars) - 1):
            # constraint: ingredient (i) - ingredient (i+1) >= 0
            relative_constraint = solver.Constraint(0, solver.infinity())
            relative_constraint.SetCoefficient(ingredient_numvar['numvar'], 1.0)
            relative_constraint.SetCoefficient(ingredient_numvars[i+1]['numvar'], -1.0)
            print("relative_constraint:", relative_constraint.name(), ingredient_numvar['ingredient']['id'], '>=', ingredient_numvars[i+1]['ingredient']['id'])
        
        # Recursively apply parent ingredient constraint and relative constraints to child ingredients
        if 'child_numvars' in ingredient_numvar:
            add_relative_constraints_on_ingredients(solver, ingredient_numvar, ingredient_numvar['child_numvars'])

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
        relative_constraint.SetCoefficient(ingredient_numvar['numvar'], coefficient)

# add maximum quantity constraints on some ingredients like en:salt (5g) and en:flavouring (1g)
def add_maximum_quantity_constraints(solver, ingredient_numvars):
    for ingredient_numvar in ingredient_numvars:
        ingredient = ingredient_numvar['ingredient']
        if ('child_numvars' in ingredient_numvar):
            add_maximum_quantity_constraints(solver, ingredient_numvar['child_numvars'])
        else:
            if ingredient['id'] == 'en:salt' or ingredient['id'] == 'en:sea-salt':
                salt_constraint = solver.Constraint(0, 5)
                salt_constraint.SetCoefficient(ingredient_numvar['numvar'], 1)
            if ingredient['id'] == 'en:flavouring' or ingredient['id'] == 'en:natural-flavouring':
                flavouring_constraint = solver.Constraint(0, 2)
                flavouring_constraint.SetCoefficient(ingredient_numvar['numvar'], 1)
            # if the ingredient is an additive (id starts with "en:e" + digits) then we set a maximum quantity of 1g
            if ingredient['id'].startswith('en:e'):
                additive_constraint = solver.Constraint(0, 2)
                additive_constraint.SetCoefficient(ingredient_numvar['numvar'], 1)

# add max limits on ingredients en:salt and en:sugar based on the sugars and salt nutrition facts of the product
def add_maximum_limits_on_salt_and_sugar(solver, ingredient_numvars, salt_constraint, sugars_constraint, fat_constraint):
    for ingredient_numvar in ingredient_numvars:
        ingredient = ingredient_numvar['ingredient']
        if ('child_numvars' in ingredient_numvar):
            add_maximum_limits_on_salt_and_sugar(solver, ingredient_numvar['child_numvars'], salt_constraint, sugars_constraint, fat_constraint)
        else:
            # salt: ingredient id is en:salt or ends with -salt
            if ingredient['id'] == 'en:salt' or ingredient['id'].endswith('-salt'):
                salt_constraint.SetCoefficient(ingredient_numvar['numvar'], 1)
            # sugar: ingredient id is en:sugar or ends with -sugar
            if ingredient['id'] == 'en:sugar' or ingredient['id'].endswith('-sugar'):
                sugars_constraint.SetCoefficient(ingredient_numvar['numvar'], 1)
            # oils: ingredient id ending with -oil, en:cocoa-butter
            if ingredient['id'].endswith('-oil') or ingredient['id'] == 'en:cocoa-butter':
                fat_constraint.SetCoefficient(ingredient_numvar['numvar'], 1)
            # fats: ingredient id ending with -fat
            if ingredient['id'].endswith('-fat'):
                fat_constraint.SetCoefficient(ingredient_numvar['numvar'], 0.8)
            # butter: min 80% fat
            if ingredient['id'] == 'en:butter':
                fat_constraint.SetCoefficient(ingredient_numvar['numvar'], 0.8)
            # butterfat: 90% fat
            if ingredient['id'] == 'en:butterfat':
                fat_constraint.SetCoefficient(ingredient_numvar['numvar'], 0.9)


# For each ingredient, get the quantity estimate from the solver (for leaf ingredients)
# or sum the quantity estimates of the child ingredients (for non-leaf ingredients)
def get_quantity_estimate(ingredient_numvars):
    total_quantity = 0
    quantity_estimate = 0
    for ingredient_numvar in ingredient_numvars:
        if ('child_numvars' in ingredient_numvar):
            quantity_estimate = get_quantity_estimate(ingredient_numvar['child_numvars'])
        else:
            quantity_estimate = ingredient_numvar['numvar'].solution_value()
            ingredient_numvar['ingredient']['lost_water'] = ingredient_numvar['lost_water'].solution_value()
        
        ingredient_numvar['ingredient']['quantity_estimate'] = quantity_estimate
        total_quantity += quantity_estimate

    return total_quantity


def set_percent_estimate(ingredients, total_quantity):
    for ingredient in ingredients:
        if ingredient.get('ingredients'):
            set_percent_estimate(ingredient['ingredients'], total_quantity)

        ingredient['percent_estimate'] = 100 * ingredient['quantity_estimate'] / total_quantity


def add_nutrient_distance(ingredient_numvars, nutrient_key, positive_constraint, negative_constraint, weighting):
    for ingredient_numvar in ingredient_numvars:
        ingredient = ingredient_numvar['ingredient']
        if 'child_numvars' in ingredient_numvar:
            #print(ingredient['indent'] + ' - ' + ingredient['text'] + ':')
            add_nutrient_distance(ingredient_numvar['child_numvars'], nutrient_key, positive_constraint, negative_constraint, weighting)
        else:
            # TODO: Figure out whether to do anything special with < ...
            # Currently treat unknown nutrients as zero percent
            ingredient_nutrient_percent =  ingredient['nutrients'].get(nutrient_key, {}).get('percent_nom', 0)
            #print(ingredient['indent'] + ' - ' + ingredient['text'] + ' (' + ingredient['ciqual_code'] + ') : ' + str(ingredient_nutrient))
            print("nutrient_distance:", ingredient['id'], nutrient_key, ingredient_nutrient_percent)
            negative_constraint.SetCoefficient(ingredient_numvar['numvar'], ingredient_nutrient_percent / 100)
            positive_constraint.SetCoefficient(ingredient_numvar['numvar'], ingredient_nutrient_percent / 100)


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

# estimate_recipe() uses a linear solver to estimate the quantities of all leaf ingredients (ingredients that don't have child ingredient)
# The solver is used to minimise the difference between the sum of the nutrients in the leaf ingredients and the total nutrients in the product
def estimate_recipe(product):
    current = time.perf_counter()
    prepare_nutrients(product)
    ingredients = product['ingredients']
    recipe_estimator = product['recipe_estimator']
    nutrients = recipe_estimator['nutrients']
    
    # Instantiate a Glop solver
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        return
    
    # Total of leaf level ingredients must add up to at least 100
    total_ingredients = solver.Constraint(100 - precision, 100 + precision, '')
    ingredient_numvars = add_ingredients_to_solver(ingredients, solver, total_ingredients)

    # Make sure nth ingredient > n+1 th ingredient
    # add_relative_constraints_on_ingredients(solver, ingredient_numvars)

    add_relative_constraints_on_ingredients(solver, None, ingredient_numvars)

    add_maximum_quantity_constraints(solver, ingredient_numvars)

    nutriments = product.get('nutriments', {})
    salt = nutriments.get('salt_100g', 0)
    salt_constraint = solver.Constraint(0, salt)

    sugar = nutriments.get('sugars_100g', 0)
    sugar_constraint = solver.Constraint(0, sugar)
    
    fat = nutriments.get('fat_100g', 0)
    fat_constraint = solver.Constraint(0, fat)

    add_maximum_limits_on_salt_and_sugar(solver, ingredient_numvars, salt_constraint, sugar_constraint, fat_constraint)

    objective = solver.Objective()
    for nutrient_key in nutrients:
        nutrient = nutrients[nutrient_key]

        weighting = nutrient.get('weighting')
        # Skip nutrients that don't have a weighting
        if weighting is None or weighting == 0:
            print("Skipping nutrient without weight:", nutrient_key)
            continue

        # We want to minimise the absolute difference between the sum of the ingredient nutrients and the total nutrients
        # Ni: Nutrient content of ingredient i
        # Ntot: Total nutrient content of product
        # i.e. minimize(abs(sum(Ni) - Ntot))
        # However we can't do absolute as it isn't linear
        # We get around this by introducing a nutrient distance variable that has to be positive
        # This is achieved by setting the following constraints:
        #    Ndist >= (Sum(Ni) - Ntot) 
        #    Ndist >= -(Sum(Ni) - Ntot) 
        # or
        #    Negative constraint:  -infinity < ( sum(Ni) - Ndist ) <= Ntot 
        #    Positive constraint:  +infinity > ( sum(Ni) + Ndist ) >= Ntot
        #
        # If the nutrition information about the ingredient is a range of value then use the higher value
        # on the positive constraint and the lower value on the negative constraint as this will make it "easier"
        # to meet these constraints
        #
        # Conversely, if the product nutrition value (Ntot) has a range then use the higher value on the negative
        # constraint and a lower value on the positive constraint

        nutrient_total = nutrient['product_total']

        nutrient_distance = solver.NumVar(0, solver.infinity(), nutrient_key)

        # not sure this is right as if one ingredient is way over and another is way under
        # then will give a good result
        negative_constraint = solver.Constraint(-solver.infinity(), nutrient_total)
        negative_constraint.SetCoefficient(nutrient_distance, -1)
        positive_constraint = solver.Constraint(nutrient_total, solver.infinity())
        positive_constraint.SetCoefficient(nutrient_distance, 1)
        add_nutrient_distance(ingredient_numvars, nutrient_key, positive_constraint, negative_constraint, weighting)

        print("nutrient_key:", nutrient_key, "nutrient_total:", nutrient_total, "weighting:", weighting)
        objective.SetCoefficient(nutrient_distance, weighting)

    add_objective_to_minimize_maximum_distance_between_ingredients(solver, objective, 0.005, ingredient_numvars)

    objective.SetMinimization()

    # Have had to keep increasing this until we get a solution for a good set of products
    # Not sure what the correct approach is here
    solver.SetSolverSpecificParametersAsString("solution_feasibility_tolerance:1e5")

    # Following may be an alternative (haven't tried yet)
    #solver_parameters = pywraplp.MPSolverParameters()
    #solver_parameters.SetDoubleParam(pywraplp.MPSolverParameters.PRIMAL_TOLERANCE, 0.001)
    #status = solver.Solve(solver_parameters)
    
    #solver.EnableOutput()

    status = solver.Solve()

    # Check that the problem has an optimal solution.
    if status == solver.OPTIMAL:
        print('An optimal solution was found in', solver.iterations(), 'iterations')
    else:
        if status == solver.FEASIBLE:
            print('A potentially suboptimal solution was found in', solver.iterations(), 'iterations')
        else:
            print('The solver could not solve the problem.')
            return status

    total_quantity = get_quantity_estimate(ingredient_numvars)
    set_percent_estimate(ingredients, total_quantity)

    end = time.perf_counter()
    recipe_estimator['time'] = end - current
    recipe_estimator['status'] = status
    recipe_estimator['iterations'] = solver.iterations()

    print('Time spent in solver: ', recipe_estimator['time'], 'seconds')

    # Calculate objective function so we can compare with SciPy
    [_, leaf_ingredients, args] = get_objective_function_args(product)
    quantities = np.array([float(ingredient['quantity_estimate']) for ingredient in leaf_ingredients])
    objective_function(quantities, *args)
    recipe_estimator['penalties'] = args[0]


    return status
