import json
from .recipe_estimator import estimate_recipe

def test_estimate_recipe_accounts_for_lost_water():
    product = {
        'code' : 1234567890123,
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'fiber': {'percent_nom': 2.5, 'percent_min': 0, 'percent_max': 100},
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
    assert round(quantity_estimate) == 200

    lost_water = ingredient.get('lost_water')
    assert round(lost_water) == 100


def test_estimate_recipe_lost_water_is_constrained():
    product = {
        'code' : 1234567890123,
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'fiber': {'percent_nom': 2.5, 'percent_min': 0, 'percent_max': 100},
                'water': {'percent_nom': 10},
            }
        }],
        'nutriments': {
            'fiber_100g': 5,
        }}


    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    # assert metrics['status'] == 0

    ingredient = product['ingredients'][0]

    # If tomatoes have a maximum water content of 10% then an original quantity of N times 90% = 100%, so N = 100 / 90 = 111
    quantity_estimate = ingredient.get('quantity_estimate')
    assert round(quantity_estimate) == 111

    lost_water = ingredient.get('lost_water')
    assert round(lost_water) == 11

def test_estimate_recipe_simple_recipe():
    # A x 15 + B x 3 = 10
    # A + B = 1
    # 15A + 3 - 3A = 10
    # A = 7 / 12 = 58%

    product = {
        'code' : 1234567890123,
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
                    'fiber': {'percent_nom': 3, 'percent_min': 0, 'percent_max': 100},
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

    assert round(product['ingredients'][0]['percent_estimate']) == 58
    assert round(product['ingredients'][1]['percent_estimate']) == 42

def test_estimate_recipe_simple_recipe_with_one_unmatched_ingredient():
    product = {
        'code' : 1234567890123,
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

def test_estimate_recipe_simple_recipe_with_no_matched_ingredients():
    product = {
        'code' : 1234567890123,
        'ingredients': [
            {
                'id':'one',
                'nutrients': {
                    'fiber': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 100},
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

def test_estimate_recipe_simple_recipe_with_no_nutriments():
    product = {
        'code' : 1234567890123,
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
                    'fiber': {'percent_nom': 3, 'percent_min': 0, 'percent_max': 100},
                }
            }
        ]}

    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    #assert metrics['status'] == 0

    assert round(product['ingredients'][0]['percent_estimate']) >= 50
    assert round(product['ingredients'][1]['percent_estimate']) <= 50

def test_estimate_recipe_subingredients():
    product = {
        'code' : 1234567890123,
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'fiber': {'percent_nom': 5, 'percent_min': 0, 'percent_max': 100},
                'water': {'percent_nom': 90, 'percent_min': 0, 'percent_max': 100},
                'sugars': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 100},
                'salt': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 100},
            }
        },
        {
            'id':'en:sugar-and-salt',
            'ingredients': [{
                'id':'en:sugar',
                'nutrients': {
                    'sugars': {'percent_nom': 100, 'percent_min': 0, 'percent_max': 100},
                    'fiber': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 100},
                    'salt': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 100},
                }
            },
            {
                'id':'en:salt',
                'nutrients': {
                    'salt': {'percent_nom': 100, 'percent_min': 0, 'percent_max': 100},
                    'fiber': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 100},
                    'sugars': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 100},
                }
            }
            ]
        }],
        'nutriments': {
            'fiber_100g': 5,
            'sugars_100g': 10,
            'salt_100g': 5
        }}

    # For the above there must by 5g of Salt and 10g of Sugar.
    # In order to make 5g of carbohydrate we need 100g of tomatoes, so there will be 15g of lost water
    # Percentages will be quantities * (100 / 115) = 4.3, 8.7 and 87
    estimate_recipe(product)

    # Print the resulting product structure
    print(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    #assert metrics['status'] == 0


    tomatoes = product['ingredients'][0]
    # Percent estimate is relative to total ingredient quantities
    assert round(tomatoes.get('percent_estimate')) == 87
    # Quantity estimate gives original quantity of ingredient per 100g/ml of product
    assert round(tomatoes.get('quantity_estimate')) == 100
    assert round(tomatoes.get('lost_water')) == 15

    sugar = product['ingredients'][1]['ingredients'][0]
    assert round(sugar.get('percent_estimate')) == 9
    assert round(sugar.get('quantity_estimate')) == 10

    salt = product['ingredients'][1]['ingredients'][1]
    assert round(salt.get('percent_estimate')) == 4
    assert round(salt.get('quantity_estimate')) == 5


def test_estimate_recipe_minimize_maximum_distance_between_ingredients():
    product = {
        'code' : 1234567890123,
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
                    'fiber': {'percent_nom': 15, 'percent_min': 0, 'percent_max': 100},
                }
            },
            {
                'id':'three',
                'nutrients': {
                    'fiber': {'percent_nom': 15, 'percent_min': 0, 'percent_max': 100},
                }
            },
            {
                'id':'four',
                'nutrients': {
                    'fiber': {'percent_nom': 15, 'percent_min': 0, 'percent_max': 100},
                }
            }
        ],
        'nutriments': {
            'fiber_100g': 60,
        }}

    # For 4 ingredients in the absence of anything better we want
    # the first ingredient to be 50 / (1 - 0.5 ^ 4) = 53.3
    # Each subsequent one half that, so 26.7, 13.3, 6.7

    estimate_recipe(product)

    # Pretty print with indents the resulting product structure
    print(json.dumps(product, indent=4))

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    assert metrics['status'] == 0

    assert round(product['ingredients'][0]['percent_estimate']) == 40
    assert round(product['ingredients'][1]['percent_estimate']) == 30
    assert round(product['ingredients'][2]['percent_estimate']) == 20
    assert round(product['ingredients'][3]['percent_estimate']) == 10


def test_estimate_recipe_minimize_maximum_distance_between_ingredients_with_subingredients():
    product = {
        'code' : 1234567890123,
        'ingredients': [
            {
                'id':'one',
                'ingredients': [
                    {
                        'id':'two',
                        'nutrients': {
                            'fiber': {'percent_nom': 15, 'percent_min': 0, 'percent_max': 100},
                        }
                    },
                    {
                        'id':'three',
                        'nutrients': {
                            'fiber': {'percent_nom': 15, 'percent_min': 0, 'percent_max': 100},
                        }
                    },
                ]
            },
            {
                'id':'four',
                'nutrients': {
                    'fiber': {'percent_nom': 15, 'percent_min': 0, 'percent_max': 100},
                }
            }
        ],
        'nutriments': {
            'fiber_100g': 45,
        },
    }

    # For 2 ingredients in the absence of anything better we want
    # the first ingredient to be (0.5 * 100) / (1 - 0.5 ^ 2) = 66.7%
    # Each subsequent one half that, so ingredient 4 should be 33.3%
    # For the sub-ingredients of ingredient one the first should be
    # (0.5 * 66.7) / (1 - 0.5 ^ 2) = 44.4%
    # So the second would be 22.2%
    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Estimates shouldn't vary too far from original values as no ingredient is any better than the others
    assert 40 < product['ingredients'][0]['ingredients'][0]['percent_estimate'] < 50 # 44.4
    assert 20 < product['ingredients'][0]['ingredients'][1]['percent_estimate'] < 25 # 22.2
    assert 30 < product['ingredients'][1]['percent_estimate'] < 40 # 33.3
