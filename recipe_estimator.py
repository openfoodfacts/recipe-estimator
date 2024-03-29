import time  
from ortools.linear_solver import pywraplp

from prepare_nutrients import prepare_nutrients

precision = 0.01


def add_ingredients_to_solver(ingredients, solver, total_ingredients):
    ingredient_numvars = []

    for i,ingredient in enumerate(ingredients):

        ingredient_numvar = {'ingredient': ingredient, 'numvar': solver.NumVar(0.0, solver.infinity(), '')}
        ingredient_numvars.append(ingredient_numvar)
        # TODO: Known percentage or stated range

        if ('ingredients' in ingredient):
            # Child ingredients
            child_numvars = add_ingredients_to_solver(ingredient['ingredients'], solver, total_ingredients)

            ingredient_numvar['child_numvars'] = child_numvars

        else:
            # Constrain water loss. If ingredient is 20% water then
            # raw ingredient - lost water must be greater than 80
            # ingredient - water_loss >= ingredient * (100 - water_ratio) / 100
            # ingredient - water_loss >= ingredient - ingredient * water ratio / 100
            # ingredient * water ratio / 100 - water_loss >= 0
            #print(ingredient['text'], ingredient['water_content'])
            ingredient_numvar['lost_water'] = solver.NumVar(0, solver.infinity(), '')
            water = ingredient['nutrients'].get('water', {})
            maximum_water_content = water.get('percent_max', 0)

            water_loss_ratio_constraint = solver.Constraint(0, solver.infinity(),  '')
            water_loss_ratio_constraint.SetCoefficient(ingredient_numvar['numvar'], 0.01 * maximum_water_content)
            water_loss_ratio_constraint.SetCoefficient(ingredient_numvar['lost_water'], -1.0)

            total_ingredients.SetCoefficient(ingredient_numvar['numvar'], 1)
            total_ingredients.SetCoefficient(ingredient_numvar['lost_water'], -1.0)

    return ingredient_numvars

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
        #print(relative_constraint.name(), ingredient_numvar['ingredient']['text'], coefficient)
        relative_constraint.SetCoefficient(ingredient_numvar['numvar'], coefficient)

def get_quantity_estimate(ingredient_numvars):
    total_quantity = 0
    for ingredient_numvar in ingredient_numvars:
        if ('child_numvars' in ingredient_numvar):
            total_quantity += get_quantity_estimate(ingredient_numvar['child_numvars'])
        else:
            quantity_estimate = ingredient_numvar['numvar'].solution_value()
            ingredient_numvar['ingredient']['quantity_estimate'] = quantity_estimate
            ingredient_numvar['ingredient']['evaporation'] = ingredient_numvar['lost_water'].solution_value()
            total_quantity += quantity_estimate

    return total_quantity


def set_percent_estimate(ingredients, total_quantity):
    for ingredient in ingredients:
        if ('ingredients' in ingredient):
            set_percent_estimate(ingredient['ingredients'], total_quantity)
        else:
            ingredient['percent_estimate'] = 100 * ingredient['quantity_estimate'] / total_quantity


def add_nutrient_distance(ingredient_numvars, nutrient_key, positive_constraint, negative_constraint, weighting):
    for ingredient_numvar in ingredient_numvars:
        ingredient = ingredient_numvar['ingredient']
        if 'child_numvars' in ingredient_numvar:
            #print(ingredient['indent'] + ' - ' + ingredient['text'] + ':')
            add_nutrient_distance(ingredient_numvar['child_numvars'], nutrient_key, positive_constraint, negative_constraint, weighting)
        else:
            # TODO: Figure out whether to do anything special with < ...
            ingredient_nutrient =  ingredient['nutrients'][nutrient_key]
            #print(ingredient['indent'] + ' - ' + ingredient['text'] + ' (' + ingredient['ciqual_code'] + ') : ' + str(ingredient_nutrient))
            negative_constraint.SetCoefficient(ingredient_numvar['numvar'], ingredient_nutrient['percent_min'] / 100)
            positive_constraint.SetCoefficient(ingredient_numvar['numvar'], ingredient_nutrient['percent_max'] / 100)


def estimate_recipe(product):
    current = time.perf_counter()
    prepare_nutrients(product)
    ingredients = product['ingredients']
    recipe_estimator = product['recipe_estimator']
    nutrients = recipe_estimator['nutrients']
    
    """Linear programming sample."""
    # Instantiate a Glop solver, naming it LinearExample.
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        return
    
    # Total of top level ingredients must add up to at least 100
    total_ingredients = solver.Constraint(100 - precision, 100 + precision, '')
    ingredient_numvars = add_ingredients_to_solver(ingredients, solver, total_ingredients)

    # Make sure nth ingredient > n+1 th ingredient
    for i,ingredient_numvar in enumerate(ingredient_numvars):
        if i < (len(ingredient_numvars) - 1):
            relative_constraint = solver.Constraint(0, solver.infinity())
            add_to_relative_constraint(solver, relative_constraint, ingredient_numvar, 1.0)
            add_to_relative_constraint(solver, relative_constraint, ingredient_numvars[i+1], -1.0)

    objective = solver.Objective()
    for nutrient_key in nutrients:
        nutrient = nutrients[nutrient_key]

        weighting = nutrient.get('weighting')
        # Skip nutrients that don't have a weighting
        if weighting is None:
            continue

        # We want to minimise the absolute difference between the sum of the ingredient nutients and the total nutrients
        # i.e. minimize(abs(sum(Ni) - Ntot))
        # However we can't do absolute as it isn't linear
        # We get around this by introducing a nutrient distance varaible that has to be positive
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
        #weighting = 1

        nutrient_distance = solver.NumVar(0, solver.infinity(), nutrient_key)

        # not sure this is right as if one ingredient is way over and another is way under
        # then will give a good result
        negative_constraint = solver.Constraint(-solver.infinity(), nutrient_total)
        negative_constraint.SetCoefficient(nutrient_distance, -1)
        positive_constraint = solver.Constraint(nutrient_total, solver.infinity())
        positive_constraint.SetCoefficient(nutrient_distance, 1)
        #print(nutrient_key, nutrient_total, weighting)
        add_nutrient_distance(ingredient_numvars, nutrient_key, positive_constraint, negative_constraint, weighting)

        objective.SetCoefficient(nutrient_distance, weighting)

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

    return status
