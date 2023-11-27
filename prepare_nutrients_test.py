from prepare_nutrients import prepare_nutrients, round_to_n


def test_prepare_nutrients():
    product = {
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'carbohydrates': {'percent_min': 2.5,'percent_max': 2.5},
                'energy': {'percent_min': 80,'percent_max': 80},
                'water': {'percent_min': 90,'percent_max': 90},
            }
        }],
        'nutriments': {
            'carbohydrates': 5,
            'protien': 4,
            'energy': 160,
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
    assert nutrient.get('weighting') == 0.2

    # Nutrients not on any ingredient are not included
    assert nutrients.get('protien') is None

    # Water is included
    assert nutrients.get('water') is not None

    # Enery is not weighted
    energy = nutrients.get('energy')
    assert energy.get('weighting') is None


def test_prepare_nutrients_copes_with_no_product_nutrients():
    product = {
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'carbohydrates': {'percent_min': 2.5,'percent_max': 2.5},
                'energy': {'percent_min': 80,'percent_max': 80},
                'water': {'percent_min': 90,'percent_max': 90},
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
    assert nutrient.get('weighting') is None

def test_round_to_n():
    assert round_to_n(1.6666666666, 3) == 1.67
    assert round_to_n(1 / 3, 4) == 0.3333
    assert round_to_n(5 / 3, 4) == 1.667

