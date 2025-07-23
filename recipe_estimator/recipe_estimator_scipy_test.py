import json

from recipe_estimator.nutrients import prepare_product
from .recipe_estimator_scipy import estimate_recipe, assign_penalty

def test_assign_penalty_value_equals_nominal():
    assert assign_penalty(10, 10, 1, 1, 100, 10) == 0

def test_assign_penalty_value_shallow_gradient_used_within_tolerance():
    # Value is half way between nominal and min so penalty = 0.5 * 2
    assert assign_penalty(35, 50, 2, 20, 70, 10) == 1
    
    # Value is half way between nominal and max so penalty = 0.5 * 2
    assert assign_penalty(60, 50, 2, 20, 70, 10) == 1

def test_assign_penalty_value_steep_gradient_used_outside_tolerance():
    # Penalty of 2 at the min plus 500 * (0.20 - 0.10) below min = 5002
    assert assign_penalty(10, 50, 2, 20, 80, 500) == 5002
    # Penalty of 2 at the max plus 500 * (100 - 80) after max = 10002
    assert assign_penalty(100, 50, 2, 20, 80, 500) == 10002


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


def test_estimate_recipe_lost_water_is_constrained():
    product = {
        'code': 'test', 
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'fiber': {'percent_nom': 2.5, 'percent_min': 2.5, 'percent_max': 2.5},
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

    # Tomatoes have a maximum water content of 10% and the algorithm only expects at most 50% of this to evaporate
    # So an original quantity of N times 95% = 100%, so N = 100 / (100 - (0.5 * 10)) = 105
    quantity_estimate = ingredient.get('quantity_estimate')
    assert round(quantity_estimate) == 105

    # lost_water = ingredient.get('lost_water')
    # assert round(lost_water) == 11

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

def test_estimate_recipe_simple_recipe_with_no_matched_ingredients():
    product = {
        'code': 'test', 
        'ingredients': [
            {
                'id':'one',
                'nutrients': {}
            },
            {
                'id':'two',
                'nutrients': {}
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
    
    # Default estimate should be such that ingredient 1 is 2 times ingredient 2. So percentages should be 67% and 33%

    assert abs(67 - product['ingredients'][0]['percent_estimate']) < 1
    assert abs(33 - product['ingredients'][1]['percent_estimate']) < 1
    assert round(product['ingredients'][0]['percent_estimate'] + product['ingredients'][1]['percent_estimate']) == 100

def test_estimate_recipe_simple_recipe_with_no_nutriments():
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


def test_estimate_recipe_minimize_maximum_distance_between_ingredients():
    product = {
        'code': 'test', 
        'ingredients': [
            {
                'id':'one',
                'nutrients': {
                    'fiber': {'percent_nom': 15, 'percent_min': 15, 'percent_max': 15},
                }
            },
            {
                'id':'two',
                'nutrients': {
                    'fiber': {'percent_nom': 15, 'percent_min': 15, 'percent_max': 15},
                }
            },
            {
                'id':'three',
                'nutrients': {
                    'fiber': {'percent_nom': 15, 'percent_min': 15, 'percent_max': 15},
                }
            },
            {
                'id':'four',
                'nutrients': {
                    'fiber': {'percent_nom': 15, 'percent_min': 15, 'percent_max': 15},
                }
            }
        ],
        'nutriments': {
            'fiber_100g': 15,
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
    #assert metrics['status'] == 0

    # Estimates shouldn't vary too far from original values as no ingredient is any better than the others
    assert 51 < product['ingredients'][0]['percent_estimate'] < 55 # 53.3
    assert 25 < product['ingredients'][1]['percent_estimate'] < 29 # 26.7
    assert 11 < product['ingredients'][2]['percent_estimate'] < 15 # 13.3
    assert 5  < product['ingredients'][3]['percent_estimate'] < 9  # 6.7
    
    
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
                            'salt': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                        }
                    },
                    {
                        'id':'en:two',
                        'nutrients': {
                            'salt': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                        }
                    }
                ]
            },
            {
                'id':'en:salt',
                'nutrients': {
                    'salt': {'percent_nom': 100, 'percent_min': 100, 'percent_max': 100},
                }
            },
        ],
        'nutriments': {
            'salt_100g': 100
        }}

    # For the above there is no way to reach the salt limit as the only ingredient with salt is in second place
    # so can be at most 50%
    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    salt = product['ingredients'][1]
    # Percent estimate is as high a possible
    assert abs(50 - salt.get('percent_estimate')) < 2


def test_estimate_recipe_minimize_maximum_distance_between_ingredients_with_subingredients():
    product = {
        'code': 'test', 
        'ingredients': [
            {
                'id':'one',
                'ingredients': [
                    {
                        'id':'two',
                        'nutrients': {
                            'fiber': {'percent_nom': 15, 'percent_min': 15, 'percent_max': 15},
                        }
                    },
                    {
                        'id':'three',
                        'nutrients': {
                            'fiber': {'percent_nom': 15, 'percent_min': 15, 'percent_max': 15},
                        }
                    },
                ]
            },
            {
                'id':'four',
                'nutrients': {
                    'fiber': {'percent_nom': 15, 'percent_min': 15, 'percent_max': 15},
                }
            }
        ],
        'nutriments': {
            'fiber_100g': 15,
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

def test_estimate_recipe_one_matched_in_the_middle():
    product = {
        'code': 'test', 
        'ingredients': [
            {
                'id':'one',
                'nutrients': {}
            },
            {
                'id':'two',
                'nutrients': {}
            },
            {
                'id':'three',
                'nutrients': {'fiber': {'percent_nom': 40, 'percent_min': 40, 'percent_max': 40}}
            },
            {
                'id':'four',
                'nutrients': {}
            },
            {
                'id':'five',
                'nutrients': {}
            },
        ],
        'nutriments': {
            'fiber_100g': 10,
        }}

    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    assert round(sum([ingredient['percent_estimate'] for ingredient in product['ingredients']])) == 100

    # There has to be 25% of the third ingredient as it is the only one the contains fiber
    assert abs(25 - product['ingredients'][2]['percent_estimate']) < 2

    # The others should be aiming for 50% of the previous ingredient but this would give
    # 100%, 50%, 25%, 12.5%, 6.75% which is more than 100%.
    # Not sure what the best guess is so following are fairly approximate

    assert abs(35 - product['ingredients'][0]['percent_estimate']) < 2
    assert abs(26 - product['ingredients'][1]['percent_estimate']) < 2

    assert abs(11 - product['ingredients'][3]['percent_estimate']) < 2
    assert abs(5 - product['ingredients'][4]['percent_estimate']) < 2

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
    
    assert abs(80 - product['ingredients'][0]['percent_estimate']) < 2
    assert abs(20 - product['ingredients'][1]['percent_estimate']) < 2

