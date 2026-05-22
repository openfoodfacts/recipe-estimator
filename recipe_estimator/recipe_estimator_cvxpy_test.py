from pytest import approx

from recipe_estimator.recipe_estimator_cvxpy import estimate_recipe


def test_estimate_recipe_simple_recipe():
    # 15A + 3B = 10
    # A + B = 1
    # 15A + 3(1 - A) = 10
    # A = 7 / 12 = 58.3%

    product = {
        'code': 'test', 
        'ingredients': [
            {
                'id':'A',
                'nutrients': {
                    'fiber': {'percent_nom': 15, 'percent_min': 15, 'percent_max': 15},
                }
            },
            {
                'id':'B',
                'nutrients': {
                    'fiber': {'percent_nom': 3, 'percent_min': 3, 'percent_max': 3},
                }
            }
        ],
        'nutriments': {
            'fiber_100g': 10,
        }}

    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    #assert metrics['status'] == 0

    assert abs(58.3 - product['ingredients'][0]['percent_estimate']) < 2
    assert abs(41.7 - product['ingredients'][1]['percent_estimate']) < 2


def test_estimate_recipe_subingredient_limits():
    product = {
        'code': 'subingredients',
        'ingredients': [
            {
                'id':'en:dummy-ingredients',
                'ingredients': [
                    {
                        'id':'en:one',
                        'nutrients': {
                            'proteins': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                        }
                    },
                    {
                        'id':'en:two',
                        'nutrients': {
                            'proteins': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                        }
                    }
                ]
            },
            {
                'id':'en:proteins',
                'nutrients': {
                    'proteins': {'percent_nom': 1, 'percent_min': 100, 'percent_max': 100},
                }
            },
        ],
        'nutriments': {
            'proteins_100g': 1
        }}

    # For the above there is no way to reach the proteins limit as the only ingredient with proteins is in second place
    # so can be at most 50%. Note use low values so that the nutrient variance is not too high which would cause it to switch to the simple approach
    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    proteins = product['ingredients'][1]
    # Percent estimate is as high a possible
    assert abs(50 - proteins.get('percent_estimate')) < 2
