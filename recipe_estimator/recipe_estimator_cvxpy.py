import time
import cvxpy as cp
import numpy as np

from .fitness import get_objective_function_args, objective as objective_function

from .prepare_nutrients import prepare_nutrients
from .nutrients import ensure_float

POWER = -1.7
EVAPORATION_COST = 0.01
UNKNOWN_INGREDIENT_WEIGHTING = 0.002


def get_ingredient_range(ingredient_percentage):
    if int(ingredient_percentage) == ingredient_percentage:
        # If percentage is an integer then assume standard rounding has been used
        return ingredient_percentage - 0.5, ingredient_percentage + 0.5
    else:
        # If decimals have been used then assume they have rounded to the nearest 0.5%
        return ingredient_percentage - 0.25, ingredient_percentage + 0.25


def add_ingredient_constraints(
    ingredients,
    nutrients,
    constraints,
    leaf_ingredients,
    ingredient_quantities,
    water_proportions,
    ingredient_vars,
    nutrients_from_ingredients = None,
):
    is_top_level = nutrients_from_ingredients is None
    if is_top_level:
        nutrients_from_ingredients = {
            'salt': cp.Constant(0),
            'sugars': cp.Constant(0),
            'fat': cp.Constant(0),
        }

    previous_ingredient_mixing_bowl_weight = None
    total_mixing_bowl_weight = []
    for ingredient in ingredients:
        # TODO: Remove hidden eventually
        ingredient_percent = ingredient.get("percent")
        my_index = len(leaf_ingredients)
        ingredient_var = {
            "ingredient": ingredient,
            "percent": ingredient_percent,
            "leaf_ingredient_index": my_index,
        }
        ingredient_vars.append(ingredient_var)
        if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
            # Child ingredients
            ingredient_var["ingredients"] = []
            my_mixing_bowl_weight = add_ingredient_constraints(
                ingredient["ingredients"],
                nutrients,
                constraints,
                leaf_ingredients,
                ingredient_quantities,
                water_proportions,
                ingredient_var["ingredients"],
                nutrients_from_ingredients,
            )
            # Keep a note of how many child ingredients make up the total for this parent ingredient
            last_child_index = len(leaf_ingredients)
            ingredient_var["last_child_index"] = last_child_index

            # For compound ingredients, if there is a known percentage then assume there is water loss before the entire compound ingredient is added to the mixing bowl
            if ingredient_percent is not None:
                # If we have a percentage for the ingredient then we add a pre-mixing bowl water loss variable
                # TODO: Cope with re-hydrated ingredients, like concentrates, where the water loss would be negative
                pre_mixing_bowl_water_loss = cp.Variable(nonneg=True)
                # For UK/EU quantity of raw ingredient less pre-mixing bowl water should correspond to the percentage on the packaging
                percent_min, percent_max = get_ingredient_range(ingredient_percent)
                constraints.extend([
                    (cp.sum(my_mixing_bowl_weight) - pre_mixing_bowl_water_loss) >= percent_min,
                    (cp.sum(my_mixing_bowl_weight) - pre_mixing_bowl_water_loss) <= percent_max
                ])
                my_mixing_bowl_weight.append(-pre_mixing_bowl_water_loss)
                ingredient_var["pre_mixing_bowl_water_loss"] = pre_mixing_bowl_water_loss

                if last_child_index > my_index:
                    # If child ingredients were found then we add a constraint that the pre-mixing bowl water loss of the parent
                    # can't be greater than the total quantity of those leaf ingredients multiplied by their water proportion
                    constraints.append(
                        pre_mixing_bowl_water_loss <= cp.sum(cp.multiply(ingredient_quantities[my_index:last_child_index], water_proportions[my_index:last_child_index]))
                    )
        else:
            my_quantity = ingredient_quantities[my_index]
            my_mixing_bowl_weight = [my_quantity]
            leaf_ingredients.append(ingredient)
            # Tried defaulting to a nominal value for water for unknown ingredients
            # but didn't seem to help
            water_proportion = ingredient["nutrients"].get("water", {}).get("percent_nom", 0) * 0.01
            water_proportions.append(water_proportion)

            if ingredient_percent is not None:
                # If we have a percentage for the ingredient then we add a pre-mixing bowl water loss variable
                pre_mixing_bowl_water_loss = cp.Variable(nonneg=True)
                ingredient_var["pre_mixing_bowl_water_loss"] = pre_mixing_bowl_water_loss
                # For UK/EU quantity of raw ingredient less pre-mixing bowl water should correspond to the percentage on the packaging
                percent_min, percent_max = get_ingredient_range(ingredient_percent)
                constraints.extend([
                    pre_mixing_bowl_water_loss <= my_quantity * water_proportion,
                    (my_quantity - pre_mixing_bowl_water_loss) >= percent_min,
                    (my_quantity - pre_mixing_bowl_water_loss) <= percent_max
                ])
                my_mixing_bowl_weight.append(-pre_mixing_bowl_water_loss)

            ingredient_id = ingredient.get("id", "")

            # Add constraint for flavour ingredients and food additives, except for first leaf ingredient
            if my_index > 0:
                if "flavour" in ingredient_id or (ingredient_id.startswith("en:e") and len(ingredient_id) > 4 and ingredient_id[4].isdigit()):
                    constraints.append(my_quantity <= 2.0)

            # If we are certain the ingredient contains a minimum amount of salt, sugar or fat
            # we add it to the expressions so that we can add constraints to keep the total below the product's nutritional information
            if ingredient_id == 'en:salt' or ingredient_id.endswith('-salt'):
                nutrients_from_ingredients['salt'] += my_quantity
            elif ingredient_id == 'en:sugar' or ingredient_id.endswith('-sugar'):
                nutrients_from_ingredients['sugars'] += my_quantity
            elif ingredient_id == 'en:honey' or ingredient_id.endswith('-honey'):
                nutrients_from_ingredients['sugars'] += 0.6 * my_quantity
            elif ingredient_id.endswith('-oil') or ingredient_id == 'en:cocoa-butter':
                nutrients_from_ingredients['fat'] += my_quantity
            elif ingredient_id.endswith('-fat'):
                nutrients_from_ingredients['fat'] += 0.8 * my_quantity
            elif ingredient_id == 'en:butter':
                nutrients_from_ingredients['fat'] += 0.8 * my_quantity
            elif ingredient_id == 'en:butterfat':
                nutrients_from_ingredients['fat'] += 0.9 * my_quantity

        if previous_ingredient_mixing_bowl_weight and my_mixing_bowl_weight:
            constraints.append(sum(previous_ingredient_mixing_bowl_weight) >= sum(my_mixing_bowl_weight))

        total_mixing_bowl_weight.extend(my_mixing_bowl_weight)
        previous_ingredient_mixing_bowl_weight = my_mixing_bowl_weight

    # If we are at the top level and we have nutritional information for the product
    # we add constraints to keep the total salt, sugar and fat below the product's nutritional information
    # We do this because processing (e.g. evaporation) should not reduce the total amount of salt, sugar or fat in the product
    if is_top_level and constraints is not None and nutrients is not None:
        salt = nutrients.get('salt')
        if salt is not None:
            constraints.append(nutrients_from_ingredients['salt'] <= ensure_float(salt))

        sugars = nutrients.get('sugars')
        if sugars is not None:
            constraints.append(nutrients_from_ingredients['sugars'] <= ensure_float(sugars))

        fat = nutrients.get('fat')
        if fat is not None:
            constraints.append(nutrients_from_ingredients['fat'] <= ensure_float(fat))

    return total_mixing_bowl_weight


def estimate_percentages(
    ingredient_quantities,
    nutrient_optimization_objectives,
    simple_optimization_objectives,
    ingredients,
    initial_estimates,
    total=100.0,
    index=0,
    percent_unknown=0,
):
    # If called with a total then we use a power-law series to estimate the percentages of each ingredient based on its position in the list of ingredients
    # Each ingredient quantity = a * n ^ p
    # where p is the POWER constant, n is the ingredient number and a is the percentage of the first ingredient
    # We work out a by adding up all the results of the series with a = 1 and then factor a so that the total adds up to 100% (total)
    # The initial_estimates array is then populated with these values. If no total is supplied we assume initial_estimates has already been populated.
    num_ingredients = len(ingredients)
    if num_ingredients < 1:
        return 0, 100

    if total is not None:
        raw_sum = sum([(n + 1.0) ** POWER for n in range(num_ingredients)])
        a = total / raw_sum

    for n, ingredient in enumerate(ingredients):
        if total is None:
            initial_estimate = initial_estimates[index]
        else:
            initial_estimate = round(a * (n + 1.0) ** POWER, 2)

        if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
            index, percent_unknown = estimate_percentages(
                ingredient_quantities,
                nutrient_optimization_objectives,
                simple_optimization_objectives,
                ingredient["ingredients"],
                initial_estimates,
                initial_estimate if total is not None else None,
                index,
                percent_unknown,
            )
        else:
            # If ingredient has no nutrient information then add an objective to keep close to the initial estimate
            if len(ingredient["nutrients"]) == 0:
                percent_unknown += initial_estimate
                nutrient_optimization_objectives.append(
                    UNKNOWN_INGREDIENT_WEIGHTING
                    * cp.square(ingredient_quantities[index] - initial_estimate)
                )
            # All ingredients aim to be as close as possible to the initial estimate when using simple optimization
            simple_optimization_objectives.append(cp.square(ingredient_quantities[index] - initial_estimate))
            if total is not None:
                initial_estimates.append(initial_estimate)

            index += 1

    return index, percent_unknown


def set_percentages(solution_x, ingredient_vars, product_total_quantity):
    total_mixing_bowl_quantity = 0
    total_original_quantity = 0
    for ingredient_var in ingredient_vars:
        ingredient = ingredient_var["ingredient"]
        pre_mixing_bowl_water_loss = ingredient_var.get("pre_mixing_bowl_water_loss")
        pre_mixing_bowl_water_loss_value = (
            pre_mixing_bowl_water_loss.value
            if pre_mixing_bowl_water_loss is not None
            and pre_mixing_bowl_water_loss.value is not None
            else 0
        )
        if "ingredients" in ingredient_var:
            index, mixing_bowl_quantity_estimate, original_quantity_estimate = set_percentages(
                solution_x, ingredient_var["ingredients"], product_total_quantity
            )
            # Subtract the parent ingredient's pre-mixing bowl water loss from the mixing bowl quantity estimate of the child ingredients to get the mixing bowl estimate for the parent ingredient
            mixing_bowl_quantity_estimate = mixing_bowl_quantity_estimate - pre_mixing_bowl_water_loss_value
        else:
            index = ingredient_var["leaf_ingredient_index"]
            raw_ingredient_quantity = solution_x[index]
            original_quantity_estimate = raw_ingredient_quantity
            mixing_bowl_quantity_estimate = original_quantity_estimate - pre_mixing_bowl_water_loss_value

        ingredient["percent_estimate"] = round(100 * mixing_bowl_quantity_estimate / product_total_quantity, 2)
        ingredient["quantity_estimate"] = round(original_quantity_estimate, 2)
        total_mixing_bowl_quantity += mixing_bowl_quantity_estimate
        total_original_quantity += original_quantity_estimate

    return index, total_mixing_bowl_quantity, total_original_quantity


def estimate_recipe(product, use_simple_estimates=False):
    current = time.perf_counter()
    leaf_ingredient_count = prepare_nutrients(product, True)
    ingredients = product["ingredients"]
    recipe_estimator = product["recipe_estimator"]
    nutrients = recipe_estimator["nutrients"]

    leaf_ingredients = []
    water_proportions = []

    ingredient_quantities = cp.Variable(leaf_ingredient_count, nonneg=True)
    constraints = []
    nutrient_weightings = []
    ingredient_vars = []
    add_ingredient_constraints(
        ingredients,
        nutrients,
        constraints,
        leaf_ingredients,
        ingredient_quantities,
        water_proportions,
        ingredient_vars,
    )

    # Hard constraint: sum of ingredients less maximum water loss can't be greater than 100g
    constraints.append(
        cp.sum(ingredient_quantities) - (ingredient_quantities @ water_proportions)
        <= 100
    )

    # Pass 1A: Run estimate_percentages to get initial estimates for the ingredient quantities and objectives
    # Initial estimates are based on a power-law series.
    simple_objectives1 = []
    initial_estimates = []
    estimate_percentages(
        ingredient_quantities, [], simple_objectives1, ingredients, initial_estimates
    )

    # Pass 1B: Run the solver with simple objectives

    evaporation_cost = EVAPORATION_COST * cp.square(sum(ingredient_quantities) - 100)
    objectives1 = list(simple_objectives1)
    objectives1.append(evaporation_cost)

    prob1 = cp.Problem(cp.Minimize(sum(objectives1)), constraints)
    prob1.solve()

    pass1_solution = ingredient_quantities.value if prob1.status == cp.OPTIMAL else initial_estimates

    # Pass 2A: Run estimate_percentages again to get updated objectives + new percent unknown based on the solution from pass 1B (if we have one)

    nutrient_objectives = []
    _, percent_unknown = estimate_percentages(
        ingredient_quantities, nutrient_objectives, [], ingredients, pass1_solution, total=None
    )

    # Pass 2B (optional): If we have nutrient information for the product and the ingredients,
    # and if the percent unknown is low, then we try to solve with nutrient objectives

    try_nutrients = False if use_simple_estimates else (percent_unknown < 10 and len(leaf_ingredients[0]["nutrients"]))

    final_solution = pass1_solution
    final_prob = prob1
    nutrient_variance_value = None
    
    product_nutrients = []
    if try_nutrients:
        # Gather ingredient nutrient quantities to an objective to minimize nutrient variance
        ingredients_nutrients = []
        for nutrient_key in nutrients:
            nutrient = nutrients[nutrient_key]

            weighting = nutrient.get("weighting", 0)
            # Skip nutrients that don't have a weighting
            if weighting == 0:
                continue

            product_total = nutrient["product_total"]
            product_nutrients.append(product_total)
            nutrient_weightings.append(weighting)
            ingredient_nutrients = []

            for i, ingredient in enumerate(leaf_ingredients):
                ingredient_nutrient = ingredient["nutrients"].get(nutrient_key, {})
                ingredient_nutrient_percent = ingredient_nutrient.get("percent_nom", 0)
                ingredient_nutrients.append(ingredient_nutrient_percent * 0.01)

            ingredients_nutrients.append(ingredient_nutrients)
            
            # Tried adding a constraint that the minimum nutrient value for all ingredients can't exceed what is on the packaging
            # but it didn't improve the results
        
        # Only do nutrient optimization if we have at least one product nutrient with a weighting
        if product_nutrients:
            # Need an np.array in the matrix multiplication below
            ingredients_nutrients = np.array(ingredients_nutrients)

            residual = ingredients_nutrients @ ingredient_quantities - product_nutrients
            nutrient_variance = cp.sum(nutrient_weightings @ cp.square(residual))
            nutrient_objectives.append(nutrient_variance)

            objectives2 = list(nutrient_objectives)
            objectives2.append(evaporation_cost)

            prob2 = cp.Problem(cp.Minimize(sum(objectives2)), constraints)
            prob2.solve()

            if prob2.status == cp.OPTIMAL:
                nutrient_variance_value = nutrient_variance.value.item()
                recipe_estimator["nutrient_variance"] = nutrient_variance_value

                if nutrient_variance_value <= 2500:
                    final_solution = ingredient_quantities.value
                    final_prob = prob2

    if try_nutrients and product_nutrients and final_prob is prob1 and prob1.status == cp.OPTIMAL:
        product_nutrients_arr = np.array(product_nutrients)
        nutrient_weightings_arr = np.array(nutrient_weightings)
        residual1 = ingredients_nutrients @ np.array(pass1_solution) - product_nutrients_arr
        recipe_estimator["nutrient_variance_simple"] = float(np.sum(nutrient_weightings_arr @ np.square(residual1)))

    if final_solution is not None:
        product_total_quantity = sum(final_solution) if recipe_estimator.get('might_be_us') else 100

        set_percentages(final_solution, ingredient_vars, product_total_quantity)

        quantities = np.array(
            [float(ingredient["quantity_estimate"]) for ingredient in leaf_ingredients]
        )
        [_, _, args] = get_objective_function_args(product)
        objective_function(quantities, *args)
        recipe_estimator["penalties"] = args[0]

    recipe_estimator["status"] = 0
    recipe_estimator["status_message"] = final_prob.status
    recipe_estimator["time"] = round(time.perf_counter() - current, 2)

    return
