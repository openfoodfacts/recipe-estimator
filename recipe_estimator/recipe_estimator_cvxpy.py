import time
import cvxpy as cp
import numpy as np

from .fitness import get_objective_function_args, objective as objective_function

from .prepare_nutrients import prepare_nutrients
from .nutrients import ensure_float
from .ingredient_limits import get_quantity_max

POWER = -1.7
EVAPORATION_COST = 0.01
UNKNOWN_INGREDIENT_WEIGHTING = 0.002
# Tolerance for rounding when checking if the percents specified on the label sum to more than 100%
SPECIFIED_PERCENTS_SUM_TOLERANCE = 1
# Ingredients under 2% can be listed in any order (EU regulation 1169/2011 Article 18 and Annex VII part A)
ANY_ORDER_PERCENT = 2


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
    percent_constraints = None,
    any_order = False,
    quantity_max_constraints = None,
):
    """Add constraints for the ingredients and return the list of expressions of their mixing bowl weights.

    Constraints that do not depend on the basis of the percents specified on the label are added immediately to constraints:
    - order of ingredients (descending mixing bowl weight), except for ingredients under 2% that can be in any order
    - pre-mixing bowl water loss of an ingredient can't be greater than its water content
    - known amounts of salt, sugars and fat in ingredients can't exceed the product's nutritional information

    Constraints that are expressed as a percent are stored in percent_constraints as
    (mixing bowl weight expression, percent min, percent max):
    - percents specified on the label
    - at most 2% for ingredients listed after an ingredient under 2% (any order)
    add_percent_constraints() adds them once all the other constraints are known, as a share of the total mixing bowl
    weight of the product (recipe share) or as a quantity for 100 g of product, depending on which is feasible.

    Maximum quantities of ingredients that are always used in small amounts (flavourings, additives, ferments...,
    see ingredient_limits.py) are stored in quantity_max_constraints as (ingredient id, constraint), except for the first
    ingredient and for ingredients with a percent specified on the label.
    add_quantity_max_constraints() adds the ones that are feasible with the other constraints.

    any_order is True for the sub-ingredients of an ingredient under 2%: they are also under 2% and can be listed in any order."""
    is_top_level = nutrients_from_ingredients is None
    if is_top_level:
        nutrients_from_ingredients = {
            'salt': cp.Constant(0),
            'sugars': cp.Constant(0),
            'fat': cp.Constant(0),
        }

    previous_ingredient_mixing_bowl_weight = None
    # Once an ingredient with a specified percent under 2% is listed, the following ingredients are also under 2%
    # and can be listed in any order
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
                percent_constraints,
                # Sub-ingredients of an ingredient under 2% are also under 2% and can be listed in any order
                any_order or (ingredient_percent is not None and ingredient_percent < ANY_ORDER_PERCENT),
                quantity_max_constraints,
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
                if percent_constraints is not None:
                    percent_constraints.append((cp.sum(my_mixing_bowl_weight) - pre_mixing_bowl_water_loss, percent_min, percent_max))
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
                constraints.append(pre_mixing_bowl_water_loss <= my_quantity * water_proportion)
                if percent_constraints is not None:
                    percent_constraints.append((my_quantity - pre_mixing_bowl_water_loss, percent_min, percent_max))
                my_mixing_bowl_weight.append(-pre_mixing_bowl_water_loss)

            ingredient_id = ingredient.get("id", "")

            # Maximum quantity for ingredients like flavourings, additives and ferments, except for the first leaf ingredient
            # and if the label specifies the percent of the ingredient
            if my_index > 0 and ingredient_percent is None and quantity_max_constraints is not None:
                quantity_max = get_quantity_max(ingredient_id)
                if quantity_max is not None:
                    quantity_max_constraints.append((ingredient_id, my_quantity <= quantity_max))

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

        if any_order:
            # Instead of the order constraint, the ingredient is under 2%
            if percent_constraints is not None and my_mixing_bowl_weight:
                percent_constraints.append((cp.sum(my_mixing_bowl_weight), 0, ANY_ORDER_PERCENT))
        elif previous_ingredient_mixing_bowl_weight and my_mixing_bowl_weight:
            constraints.append(cp.sum(previous_ingredient_mixing_bowl_weight) >= cp.sum(my_mixing_bowl_weight))
        if ingredient_percent is not None and ingredient_percent < ANY_ORDER_PERCENT:
            any_order = True

        total_mixing_bowl_weight.extend(my_mixing_bowl_weight)
        previous_ingredient_mixing_bowl_weight = my_mixing_bowl_weight

    # If we are at the top level and we have nutritional information for the product
    # we add constraints to keep the total salt, sugar and fat below the product's nutritional information
    # We do this because processing (e.g. evaporation) should not reduce the total amount of salt, sugar or fat in the product
    if is_top_level and constraints is not None and nutrients is not None:
        salt = nutrients.get('salt',{}).get('product_total')
        if salt is not None:
            constraints.append(nutrients_from_ingredients['salt'] <= ensure_float(salt))

        sugars = nutrients.get('sugars',{}).get('product_total')
        if sugars is not None:
            constraints.append(nutrients_from_ingredients['sugars'] <= ensure_float(sugars))

        fat = nutrients.get('fat',{}).get('product_total')
        if fat is not None:
            constraints.append(nutrients_from_ingredients['fat'] <= ensure_float(fat))

    return total_mixing_bowl_weight


def specified_percents_sum_over_100(ingredients):
    specified_percents = [ingredient["percent"] for ingredient in ingredients if isinstance(ingredient.get("percent"), (int, float))]
    return sum(specified_percents) > 100 + SPECIFIED_PERCENTS_SUM_TOLERANCE


def get_percent_constraints(percent_constraints, total_mixing_bowl_weight, basis):
    """Return the constraints for the percents specified on the label, for the given basis:
    - recipe_share: percent of the total mixing bowl weight
    - per_100g: mixing bowl weight for 100 g of finished product"""
    constraints = []
    if basis == "per_100g":
        for mixing_bowl_weight, percent_min, percent_max in percent_constraints:
            constraints.extend([mixing_bowl_weight >= percent_min, mixing_bowl_weight <= percent_max])
    else:
        # cvxpy expression of the total mixing bowl weight, the actual value is determined by the solver
        total_mixing_bowl_weight_sum = cp.sum(total_mixing_bowl_weight)
        for mixing_bowl_weight, percent_min, percent_max in percent_constraints:
            constraints.extend([
                mixing_bowl_weight >= percent_min * 0.01 * total_mixing_bowl_weight_sum,
                mixing_bowl_weight <= percent_max * 0.01 * total_mixing_bowl_weight_sum,
            ])
    return constraints


def is_feasible(constraints):
    problem = cp.Problem(cp.Minimize(0), constraints)
    problem.solve()
    return problem.status == cp.OPTIMAL


def add_quantity_max_constraints(ingredients, constraints, quantity_max_constraints, percent_constraints, total_mixing_bowl_weight):
    """Add the maximum quantities of ingredients (flavourings, additives, ferments...) that are feasible with the other
    constraints, including the percents specified on the label (with either basis), and return the ids of the ingredients
    whose maximum quantity was not applied.

    A maximum can be infeasible, e.g. if an ingredient listed after the restricted ingredient has a higher percent on the label.
    Like in Product Opener's set_percent_max_from_taxonomy, we then keep the order of the ingredients and the percents of the label.

    Must be called after all other constraints except the percent constraints have been added."""
    if not quantity_max_constraints:
        return []

    if not percent_constraints:
        bases = [None]
    elif specified_percents_sum_over_100(ingredients):
        bases = ["per_100g"]
    else:
        bases = ["recipe_share", "per_100g"]

    def feasible(candidate_constraints):
        for basis in bases:
            basis_constraints = [] if basis is None else get_percent_constraints(percent_constraints, total_mixing_bowl_weight, basis)
            if is_feasible(constraints + candidate_constraints + basis_constraints):
                return True
        return False

    all_constraints = [constraint for _, constraint in quantity_max_constraints]
    if feasible(all_constraints):
        constraints.extend(all_constraints)
        return []

    # Add the maximums one by one, in the order of the ingredients, and skip the ones that make the problem infeasible
    kept = []
    skipped = []
    for ingredient_id, constraint in quantity_max_constraints:
        if feasible(kept + [constraint]):
            kept.append(constraint)
        else:
            skipped.append(ingredient_id)
    constraints.extend(kept)
    return skipped


def add_percent_constraints(ingredients, constraints, percent_constraints, total_mixing_bowl_weight):
    """Add constraints for the percents specified on the label, and return the basis used.

    Following EU regulation 1169/2011 Annex VIII point 3, a specified percent is in general the share of the ingredient
    in the recipe at the time the ingredients are added (mixing bowl), which is what percent_estimate is,
    so that specified percents are kept by the estimation even if water is lost after the mixing bowl (e.g. cooking).

    For foods that lost moisture, labels can instead indicate the quantity used related to the finished product
    (point 4(a), e.g. 50 g of butter in a recipe that gives 170 g of cookies: 29.4%). We can only tell when the
    specified percents sum to more than 100%, and in that case they constrain the mixing bowl weights for 100 g of product.

    Recipe shares must sum to 100%, which is not always possible with the other constraints (e.g. the order of ingredients
    when the label specifies the percents of the main ingredients and the remaining ingredients are under 2%, which
    can be listed in any order). In that case, we use the mixing bowl weights for 100 g of product.

    Must be called after all other constraints have been added.
    """
    if not percent_constraints:
        return None
    if not specified_percents_sum_over_100(ingredients):
        recipe_share_constraints = get_percent_constraints(percent_constraints, total_mixing_bowl_weight, "recipe_share")
        feasibility = cp.Problem(cp.Minimize(0), constraints + recipe_share_constraints)
        feasibility.solve()
        if feasibility.status == cp.OPTIMAL:
            constraints.extend(recipe_share_constraints)
            return "recipe_share"
    constraints.extend(get_percent_constraints(percent_constraints, total_mixing_bowl_weight, "per_100g"))
    return "per_100g"


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


def save_pre_mixing_bowl_water_loss_values(ingredient_vars, solved):
    """Save the pre-mixing bowl water loss values of the solution that we use, as the values of the variables
    are overwritten by the next solves (or are not meaningful if the solver did not find an optimal solution)"""
    for ingredient_var in ingredient_vars:
        pre_mixing_bowl_water_loss = ingredient_var.get("pre_mixing_bowl_water_loss")
        ingredient_var["pre_mixing_bowl_water_loss_value"] = (
            pre_mixing_bowl_water_loss.value
            if solved
            and pre_mixing_bowl_water_loss is not None
            and pre_mixing_bowl_water_loss.value is not None
            else 0
        )
        if "ingredients" in ingredient_var:
            save_pre_mixing_bowl_water_loss_values(ingredient_var["ingredients"], solved)


def set_percentages(solution_x, ingredient_vars, product_total_quantity):
    total_mixing_bowl_quantity = 0
    total_original_quantity = 0
    for ingredient_var in ingredient_vars:
        ingredient = ingredient_var["ingredient"]
        pre_mixing_bowl_water_loss_value = ingredient_var.get("pre_mixing_bowl_water_loss_value", 0)
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
    percent_constraints = []
    quantity_max_constraints = []
    total_mixing_bowl_weight = add_ingredient_constraints(
        ingredients,
        nutrients,
        constraints,
        leaf_ingredients,
        ingredient_quantities,
        water_proportions,
        ingredient_vars,
        percent_constraints=percent_constraints,
        quantity_max_constraints=quantity_max_constraints,
    )

    # Hard constraint: sum of ingredients must be at least 100g
    constraints.append(
        cp.sum(ingredient_quantities) >= 100
    )

    # Hard constraint: sum of ingredients less maximum water loss can't be greater than 100g
    constraints.append(
        cp.sum(ingredient_quantities) - (ingredient_quantities @ water_proportions)
        <= 100
    )

    # Maximum quantities of ingredients like flavourings, additives and ferments (needs all other constraints except percents)
    skipped_quantity_max = add_quantity_max_constraints(
        ingredients, constraints, quantity_max_constraints, percent_constraints, total_mixing_bowl_weight
    )
    if skipped_quantity_max:
        recipe_estimator["skipped_quantity_max"] = skipped_quantity_max

    # Constraints for the percents specified on the label (needs all other constraints)
    specified_percents_basis = add_percent_constraints(ingredients, constraints, percent_constraints, total_mixing_bowl_weight)
    if specified_percents_basis:
        recipe_estimator["specified_percents_basis"] = specified_percents_basis

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
    save_pre_mixing_bowl_water_loss_values(ingredient_vars, prob1.status == cp.OPTIMAL)

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
                    save_pre_mixing_bowl_water_loss_values(ingredient_vars, True)

    if try_nutrients and product_nutrients and final_prob is prob1 and prob1.status == cp.OPTIMAL:
        product_nutrients_arr = np.array(product_nutrients)
        nutrient_weightings_arr = np.array(nutrient_weightings)
        residual1 = ingredients_nutrients @ np.array(pass1_solution) - product_nutrients_arr
        recipe_estimator["nutrient_variance_simple"] = float(np.sum(nutrient_weightings_arr @ np.square(residual1)))

    if final_solution is not None:
        # percent_estimate is the share of the ingredient in the recipe at the time the ingredients are added
        # (the mixing bowl), so that percent estimates sum to 100% (EU regulation 1169/2011 Annex VIII point 3).
        # quantity_estimate is the quantity of ingredient used for 100 g of finished product, which can sum to more
        # than 100 g for products that lost water (Annex VIII point 4(a)).
        # We first compute the total quantity in the mixing bowl, then compute the percentages relative to it.
        _, total_mixing_bowl_quantity, _ = set_percentages(final_solution, ingredient_vars, 100)
        if total_mixing_bowl_quantity > 0:
            set_percentages(final_solution, ingredient_vars, total_mixing_bowl_quantity)

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
