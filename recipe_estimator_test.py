from recipe_estimator import prepare_nutrients


def test_prepare_nutrients():
    product = {
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'carbohydrates': 2.5,
                'energy': 80,
                'water': 90,
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


