from .prepare_nutrients import prepare_nutrients


def test_prepare_nutrients():
    product = {
        'code' : 1234567890123,
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'carbohydrates': {'percent_nom': 2.5},
                'energy': {'percent_nom': 80},
                'water': {'percent_nom': 90},
            }
        }],
        'nutriments': {
            'carbohydrates_100g': 5,
            'proteins_100g': 4,
            'energy_100g': 160,
        }}

    prepare_nutrients(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Ingredient count is calculated
    assert metrics['ingredient_count'] == 1

    nutrients = metrics.get('nutrients')
    assert nutrients is not None
    nutrient = nutrients.get('carbohydrates')
    assert nutrient is not None

    # Nutrient information is calculated
    assert nutrient.get('ingredient_count') == 1
    assert nutrient.get('unweighted_total') == 2.5
    # Weighting assigned based on proportion in product
    # TODO: This seems to have been disabled
    # assert nutrient.get('weighting') == 0.2

    # Nutrients not on any ingredient are not included
    assert nutrients.get('proteins') is None

    # Water is included
    assert nutrients.get('water') is not None

    # Enery is not weighted
    energy = nutrients.get('energy')
    assert energy.get('weighting') == 0


def test_prepare_nutrients_copes_with_no_product_nutrients():
    product = {
        'code' : 1234567890123,
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'carbohydrates': {'percent_nom': 2.5},
                'energy': {'percent_nom': 80},
                'water': {'percent_nom': 90},
            }
        }]}

    prepare_nutrients(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Ingredient count is calculated
    assert metrics['ingredient_count'] == 1

    nutrients = metrics.get('nutrients')
    assert nutrients is not None
    nutrient = nutrients.get('carbohydrates')
    assert nutrient is not None

    # Nutrient information flagged
    assert nutrient.get('notes') is not None
    assert nutrient.get('weighting') == 0


