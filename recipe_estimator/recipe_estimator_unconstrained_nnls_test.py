import json
from recipe_estimator.nutrients import prepare_product
from recipe_estimator.product import get_product
from .recipe_estimator_unconstrained_nnls import estimate_recipe

def test_estimate_recipe_accounts_for_lost_water():
    product = {
        'code': 'test', 
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'fiber': {'percent_nom': 4, 'percent_min': 4, 'percent_max': 4},
                'water': {'percent_nom': 90},
            }
        }],
        'nutriments': {
            'fiber_100g': 5,
        }}

    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    #assert metrics['status'] == 0

    ingredient = product['ingredients'][0]
    # Percent estimate is relative to total ingredient quantities
    percent_estimate = ingredient.get('percent_estimate')
    assert round(percent_estimate) == 100

    # Quantity estimate gives original quantity of ingredient per 100g/ml of product
    quantity_estimate = ingredient.get('quantity_estimate')
    assert round(quantity_estimate) == 125

    # lost_water = ingredient.get('lost_water')
    # assert round(lost_water) == 100


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

    # For the above there must by 5g of Salt and 10g of Sugar.
    # In order to make 5g of fibre we need 100g of tomatoes, so there will be 15g of lost water
    # Percentages will be quantities * (100 / 115) = 4.3, 8.7 and 87
    estimate_recipe(product)

    # Print the resulting product structure
    # print(json.dumps(product, indent=2))

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    #assert metrics['status'] == 0


    tomatoes = product['ingredients'][0]
    # Percent estimate is relative to total ingredient quantities
    assert abs(87 - tomatoes.get('percent_estimate')) < 2
    # Quantity estimate gives original quantity of ingredient per 100g/ml of product
    assert abs(100- tomatoes.get('quantity_estimate')) < 2
    # assert round(tomatoes.get('lost_water')) == 3

    sugar = product['ingredients'][1]['ingredients'][0]
    assert abs(9 - sugar.get('percent_estimate')) < 1
    assert abs(10 - sugar.get('quantity_estimate')) < 1

    salt = product['ingredients'][1]['ingredients'][1]
    assert abs(4 - salt.get('percent_estimate')) < 1
    assert abs(5 - salt.get('quantity_estimate')) < 11


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
    
    assert abs(80 - product['ingredients'][0]['quantity_estimate']) < 2

def test_estimate_recipe():
    product = get_product("4088600354972")
    prepare_product(product)
    estimate_recipe(product)
    assert json.dumps(product, indent=2)
    assert product["recipe_estimator"]
