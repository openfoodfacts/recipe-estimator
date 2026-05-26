import time
import cvxpy as cp
import numpy as np

from .fitness import get_objective_function_args, objective as objective_function

from .prepare_nutrients import prepare_nutrients

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
    constraints,
    leaf_ingredients,
    ingredient_quantities,
    water_proportions,
    ingredient_vars,
):
    previous_ingredient_mixing_bowl_weight = None
    total_mixing_bowl_weight = []
    for ingredient in ingredients:
        # TODO: Remove hidden eventually
        ingredient_percent = ingredient.get("percent", ingredient.get("percent_hidden"))
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
                constraints,
                leaf_ingredients,
                ingredient_quantities,
                water_proportions,
                ingredient_var["ingredients"],
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

        if previous_ingredient_mixing_bowl_weight and my_mixing_bowl_weight:
            constraints.append(sum(previous_ingredient_mixing_bowl_weight) >= sum(my_mixing_bowl_weight))

        total_mixing_bowl_weight.extend(my_mixing_bowl_weight)
        previous_ingredient_mixing_bowl_weight = my_mixing_bowl_weight

    return total_mixing_bowl_weight


def estimate_percentages(
    ingredient_quantities, nutrient_objectives, simple_objectives, ingredients, simple_estimates, total=100.0, index=0, percent_unknown = 0
):
    # Each ingredient quantity = a * n ^ p
    # where p is the POWER constant, n is the ingredient number and a is the percentage of the first ingredient
    # We work out a by adding up all the results of the series with a = 1 and then factor a so that the total adds up to 100% (total)
    num_ingredients = len(ingredients)
    if num_ingredients < 1:
        return 0, 100

    raw_sum = sum([(n + 1.0) ** POWER for n in range(num_ingredients)])
    a = total / raw_sum
    for n, ingredient in enumerate(ingredients):
        estimate = round(a * (n + 1.0) ** POWER, 2)

        if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
            index, percent_unknown = estimate_percentages(
                ingredient_quantities,
                nutrient_objectives,
                simple_objectives,
                ingredient["ingredients"],
                simple_estimates,
                estimate,
                index,
                percent_unknown
            )
        else:
            # If ingredient has no nutrient information then add an objective to keep close to the estimate
            if len(ingredient["nutrients"]) == 0:
                percent_unknown += estimate
                nutrient_objectives.append(
                    UNKNOWN_INGREDIENT_WEIGHTING
                    * cp.square(ingredient_quantities[index] - estimate)
                )
            # Simple objectives are used if we find that going by nutrients doesn't work
            simple_objectives.append(cp.square(ingredient_quantities[index] - estimate))
            simple_estimates.append(estimate)
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


def estimate_recipe(product):
    current = time.perf_counter()
    leaf_ingredient_count = prepare_nutrients(product, True)
    ingredients = product["ingredients"]
    recipe_estimator = product["recipe_estimator"]
    nutrients = recipe_estimator["nutrients"]

    ingredients_nutrients = []
    product_nutrients = []
    leaf_ingredients = []
    water_proportions = []

    ingredient_quantities = cp.Variable(leaf_ingredient_count, nonneg=True)
    constraints = []
    nutrient_weightings = []
    ingredient_vars = []
    add_ingredient_constraints(
        ingredients,
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
    
    # Need an np.array in the matrix multiplication below
    ingredients_nutrients = np.array(ingredients_nutrients)
    nutrient_objectives = []
    simple_objectives = []
    simple_estimates = []

    # Add objective to keep unknown ingredients close to the inverse power series
    # simple_objectives does this for all ingredients
    _, percent_unknown = estimate_percentages(ingredient_quantities, nutrient_objectives, simple_objectives, ingredients, simple_estimates)

    # Main objective to match ingredient nutrients to product nutrients
    if product_nutrients:
        residual = ingredients_nutrients @ ingredient_quantities - product_nutrients
        nutrient_variance = cp.sum(nutrient_weightings @ cp.square(residual))
        nutrient_objectives.append(nutrient_variance)

        # Tried adding a penalty if not all ingredients are known to penalize results where
        # the ingredient nutrients are greater than the product nutrients
        # But it didn't offer any significant improvement

    try_nutrients = percent_unknown < 10 and len(leaf_ingredients[0]["nutrients"])

    # Don't bother with the nutrient approach if the first ingredient is unknown or too many others are unknown
    objectives = nutrient_objectives if try_nutrients else simple_objectives
    
    # Get the ingredients to add up to close to 100g, which effectively adds a cost for evaporation.
    # Could potentially adjust the weighting here depending on the food category
    evaporation_cost = EVAPORATION_COST * cp.square(sum(ingredient_quantities) - 100)
    objectives.append(evaporation_cost)

    objective = cp.Minimize(sum(objectives))
    prob = cp.Problem(objective, constraints)
    prob.solve()

    if product_nutrients:
        if prob.status == cp.OPTIMAL:
            nutrient_variance_value = nutrient_variance.value.item()
            recipe_estimator["nutrient_variance"] = nutrient_variance_value

        # If nutrient variance is too much then try again with the simple approach
        if try_nutrients and (prob.status != cp.OPTIMAL or nutrient_variance_value > 2500):
            objectives = simple_objectives
            objective = cp.Minimize(sum(objectives))
            prob = cp.Problem(objective, constraints)
            prob.solve()
            if prob.status == cp.OPTIMAL:
                recipe_estimator["nutrient_variance_simple"] = nutrient_variance.value.item()

    solution_x = ingredient_quantities.value if prob.status == cp.OPTIMAL else simple_estimates
        
    # In the UK/EU the percentage is the weight of raw product needed to produce 100g divided by the final weight (100g)
    # In the US it is the weight of raw ingredient divided by the total weight of all raw ingredients
    product_total_quantity = sum(solution_x) if recipe_estimator.get('might_be_us') else 100

    set_percentages(solution_x, ingredient_vars, product_total_quantity)

    # Calculate objective function so we can compare with SciPy
    quantities = np.array(
        [float(ingredient["quantity_estimate"]) for ingredient in leaf_ingredients]
    )
    [_, _, args] = get_objective_function_args(product)
    objective_function(quantities, *args)
    recipe_estimator["penalties"] = args[0]

    recipe_estimator["status"] = 0 # TODO: Should probably have different status codes for different failure modes, e.g. not optimal vs unbounded vs infeasible
    recipe_estimator["status_message"] = prob.status
    recipe_estimator["time"] = round(time.perf_counter() - current, 2)

    # Tried re-running the solver multiple times to get the minimum and maximum of each ingredient
    # But it had a significant performance penalty

    return
