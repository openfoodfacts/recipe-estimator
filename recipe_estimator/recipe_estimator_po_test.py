from recipe_estimator.nutrients import prepare_product
from .recipe_estimator_po import estimate_recipe

def test_estimate_recipe_simple_recipe_with_one_unmatched_ingredient():
    product = {
        'code': 'test', 
        'ingredients': [
            {
                'id':'one',
                'nutrients': {
                    'fiber': {'percent_nom': 15, 'percent_min': 0, 'percent_max': 100},
                }
            },
            {
                'id':'two',
                'nutrients': {
                    'fiber': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 100},
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

    assert round(product['ingredients'][0]['percent_estimate']) >= 50
    assert round(product['ingredients'][1]['percent_estimate']) <= 50
    assert round(product['ingredients'][0]['percent_estimate'] + product['ingredients'][1]['percent_estimate']) == 100

def test_estimate_recipe_subingredients():
    product = {
        'code': 'test', 
        'ingredients': [
            {
                'id':'en:tomato',
                'nutrients': {
                    'fiber': {'percent_nom': 5, 'percent_min': 5, 'percent_max': 5},
                    'water': {'percent_nom': 90, 'percent_min': 0, 'percent_max': 100},
                    'sugars': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                    'salt': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                }
            },
            {
                'id':'en:sugar-and-salt',
                'ingredients': [{
                    'id':'en:sugar',
                    'nutrients': {
                        'sugars': {'percent_nom': 100, 'percent_min': 100, 'percent_max': 100},
                        'fiber': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                        'salt': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                    }
                },
                {
                    'id':'en:salt',
                    'nutrients': {
                        'salt': {'percent_nom': 100, 'percent_min': 100, 'percent_max': 100},
                        'fiber': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                        'sugars': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                    }
                }
                ]
            }
        ],
        'nutriments': {
            'fiber_100g': 5,
            'sugars_100g': 10,
            'salt_100g': 5
        }}

    estimate_recipe(product)

    # Print the resulting product structure
    # print(json.dumps(product, indent=2))

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    tomatoes = product['ingredients'][0]['percent_estimate']
    sugar = product['ingredients'][1]['ingredients'][0]['percent_estimate']
    salt = product['ingredients'][1]['ingredients'][1]['percent_estimate']
    assert tomatoes > sugar + salt
    assert sugar > salt
    assert abs(100 - (tomatoes + sugar + salt)) < 1


def test_ingredients_dont_add_up():
    product = {
        'code' : 'test',
        'ingredients': [
            {'id':'en:sugar'},
            {'id':'en:salt'},
        ],
        'nutriments': {
            'sugars_100g': 80
        }
    }

    prepare_product(product)
    estimate_recipe(product)
    metrics = product.get('recipe_estimator')
    assert metrics is not None
    
    sugar = product['ingredients'][0]['quantity_estimate']
    salt = product['ingredients'][1]['quantity_estimate']
    assert sugar > salt
    assert abs(100 - (sugar + salt)) < 1

