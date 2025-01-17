import time  
from ortools.math_opt.python import mathopt

from prepare_nutrients import prepare_nutrients

precision = 0.01
sf = 1000

def add_ingredients_to_solver(ingredients, model: mathopt.Model, total_ingredients: mathopt.LinearConstraint):
    ingredient_numvars = []

    for i,ingredient in enumerate(ingredients):

        ingredient_numvar = {'ingredient': ingredient, 'numvar': model.add_variable(lb = 0)}
        ingredient_numvars.append(ingredient_numvar)
        # TODO: Known percentage or stated range

        if ('ingredients' in ingredient):
            # Child ingredients
            child_numvars = add_ingredients_to_solver(ingredient['ingredients'], model, total_ingredients)

            ingredient_numvar['child_numvars'] = child_numvars

        else:
            # Constrain water loss. If ingredient is 20% water then
            # raw ingredient - lost water must be greater than 80
            # ingredient - water_loss >= ingredient * (100 - water_ratio) / 100
            # ingredient - water_loss >= ingredient - ingredient * water ratio / 100
            # ingredient * water ratio / 100 - water_loss >= 0
            
            ingredient_numvar['lost_water'] = model.add_variable(lb = 0)
            water = ingredient['nutrients'].get('water', {})
            maximum_water_content = water.get('percent_max', 0)
            print("maximum_water_content", ingredient['id'], maximum_water_content)

            water_loss_ratio_constraint = model.add_linear_constraint(lb = 0)
            water_loss_ratio_constraint.set_coefficient(ingredient_numvar['numvar'], 0.01 * maximum_water_content * sf)
            water_loss_ratio_constraint.set_coefficient(ingredient_numvar['lost_water'], -1.0 * sf)

            total_ingredients.set_coefficient(ingredient_numvar['numvar'], 1 * sf)
            total_ingredients.set_coefficient(ingredient_numvar['lost_water'], -1.0 * sf)
            print("total_ingredients:", total_ingredients.name, ingredient_numvar['ingredient']['id'])

    return ingredient_numvars

# Add constraints to ensure that the quantity of each ingredient is greater than or equal to the quantity of the next ingredient
# and that the sum of children ingredients is equal to the parent ingredient
def add_relative_constraints_on_ingredients(model: mathopt.Model, parent_ingredient_numvar, ingredient_numvars):

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

# estimate_recipe() uses a linear solver to estimate the quantities of all leaf ingredients (ingredients that don't have child ingredient)
# The solver is used to minimise the difference between the sum of the nutrients in the leaf ingredients and the total nutrients in the product
def estimate_recipe(product):
    current = time.perf_counter()
    prepare_nutrients(product)
    ingredients = product['ingredients']
    recipe_estimator = product['recipe_estimator']
    nutrients = recipe_estimator['nutrients']
    
    # Create a model
    model = mathopt.Model(name = "recipe_estimator")
    if not model:
        return
    
    # Total of leaf level ingredients must add up to at least 100
    total_ingredients = model.add_linear_constraint(lb = 100 - precision, ub = 100 + precision, name = 'ingredients must add up to 100%')
    ingredient_numvars = add_ingredients_to_solver(ingredients, model, total_ingredients)

    # Make sure nth ingredient > n+1 th ingredient
    # add_relative_constraints_on_ingredients(solver, ingredient_numvars)

    add_relative_constraints_on_ingredients(model, None, ingredient_numvars)

    objective = 0
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

        nutrient_total_from_ingredients = 0
        nutrient_total_from_ingredients = add_ingredient_nutrients(ingredient_numvars, nutrient_key, nutrient_total_from_ingredients)

        print("nutrient_key:", nutrient_key, "nutrient_total:", nutrient_total, "weighting:", weighting)
        objective += (nutrient_total * nutrient_total - 2 * nutrient_total_from_ingredients * nutrient_total + nutrient_total_from_ingredients * nutrient_total_from_ingredients) * sf

    #add_objective_to_minimize_maximum_distance_between_ingredients(solver, objective, 0.005, ingredient_numvars)
    model.minimize(objective)


    # Have had to keep increasing this until we get a solution for a good set of products
    # Not sure what the correct approach is here
    #solver.SetSolverSpecificParametersAsString("solution_feasibility_tolerance:1e5")

    # Following may be an alternative (haven't tried yet)
    #solver_parameters = pywraplp.MPSolverParameters()
    #solver_parameters.SetDoubleParam(pywraplp.MPSolverParameters.PRIMAL_TOLERANCE, 0.001)
    #status = solver.Solve(solver_parameters)
    
    #solver.EnableOutput()
    params = mathopt.SolveParameters(enable_output=True)

    # PDLP cannot solve problems with non-diagonal objective matrices
    # status = mathopt.solve(model, mathopt.SolverType.PDLP, params=params)

    # MathOpt does not currently support CP-SAT models with quadratic objectives
    # status = mathopt.solve(model, mathopt.SolverType.CP_SAT, params=params)

    # MathOpt does not currently support Highs models with quadratic objectives
    # status = mathopt.solve(model, mathopt.SolverType.HIGHS, params=params)

    # Hangs
    # status = mathopt.solve(model, mathopt.SolverType.GSCIP, params=params)

    # Not registered SCS, SANTORINI, ECOS, GLPK, OSQP. GUROBI requires a licence
    status = mathopt.solve(model, mathopt.SolverType.GLOP, params=params)

    # Check that the problem has an optimal solution.
    # if status == model.OPTIMAL:
    #     print('An optimal solution was found in', solver.iterations(), 'iterations')
    # else:
    #     if status == solver.FEASIBLE:
    #         print('A potentially suboptimal solution was found in', solver.iterations(), 'iterations')
    #     else:
    #         print('The solver could not solve the problem.')
    #         return status

    total_quantity = get_quantity_estimate(ingredient_numvars)
    set_percent_estimate(ingredients, total_quantity)

    end = time.perf_counter()
    recipe_estimator['time'] = end - current
    recipe_estimator['status'] = status
    #recipe_estimator['iterations'] = solver.iterations()

    print('Time spent in solver: ', recipe_estimator['time'], 'seconds')

    return status
