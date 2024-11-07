import json
from recipe_estimator import estimate_recipe


def test_estimate_recipe_accounts_for_lost_water():
    product = {
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'carbohydrates': {'percent_min': 2.5,'percent_max': 2.5},
                'water': {'percent_min': 90,'percent_max': 90},
            }
        }],
        'nutriments': {
            'carbohydrates_100g': 5,
        }}

    estimate_recipe(product)

    # Print the resulting product structure
    print(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    assert metrics['status'] == 0

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
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'carbohydrates': {'percent_min': 2.5,'percent_max': 2.5},
                'water': {'percent_min': 10,'percent_max': 10},
            }
        }],
        'nutriments': {
            'carbohydrates_100g': 5,
        }}

    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    assert metrics['status'] == 0

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
        'ingredients': [
            {
                'id':'one',
                'nutrients': {
                    'carbohydrates': {'percent_min': 15,'percent_max': 15},
                }
            },
            {
                'id':'two',
                'nutrients': {
                    'carbohydrates': {'percent_min': 3,'percent_max': 3},
                }
            }
        ],
        'nutriments': {
            'carbohydrates_100g': 10,
        }}

    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    assert metrics['status'] == 0

    assert round(product['ingredients'][0]['percent_estimate']) == 58
    assert round(product['ingredients'][1]['percent_estimate']) == 42

def test_estimate_recipe_simple_recipe_with_one_unmatched_ingredient():
    product = {
        'ingredients': [
            {
                'id':'one',
                'nutrients': {
                    'carbohydrates': {'percent_min': 15,'percent_max': 15},
                }
            },
            {
                'id':'two',
                'nutrients': {
                    'carbohydrates': {'percent_min': 0,'percent_max': 100},
                }
            }
        ],
        'nutriments': {
            'carbohydrates_100g': 10,
        }}

    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    assert metrics['status'] == 0

    assert round(product['ingredients'][0]['percent_estimate']) >= 50
    assert round(product['ingredients'][1]['percent_estimate']) <= 50
    assert round(product['ingredients'][0]['percent_estimate'] + product['ingredients'][1]['percent_estimate']) == 100

def test_estimate_recipe_simple_recipe_with_no_matched_ingredients():
    product = {
        'ingredients': [
            {
                'id':'one',
                'nutrients': {
                    'carbohydrates': {'percent_min': 0,'percent_max': 100},
                }
            },
            {
                'id':'two',
                'nutrients': {
                    'carbohydrates': {'percent_min': 0,'percent_max': 100},
                }
            }
        ],
        'nutriments': {
            'carbohydrates_100g': 10,
        }}

    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    assert metrics['status'] == 0

    assert round(product['ingredients'][0]['percent_estimate']) >= 50
    assert round(product['ingredients'][1]['percent_estimate']) <= 50
    assert round(product['ingredients'][0]['percent_estimate'] + product['ingredients'][1]['percent_estimate']) == 100

def test_estimate_recipe_simple_recipe_with_no_nutriments():
    product = {
        'ingredients': [
            {
                'id':'one',
                'nutrients': {
                    'carbohydrates': {'percent_min': 15,'percent_max': 15},
                }
            },
            {
                'id':'two',
                'nutrients': {
                    'carbohydrates': {'percent_min': 3,'percent_max': 3},
                }
            }
        ]}

    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    assert metrics['status'] == 0

    assert round(product['ingredients'][0]['percent_estimate']) >= 50
    assert round(product['ingredients'][1]['percent_estimate']) <= 50

def test_estimate_recipe_subingredients():
    product = {
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'carbohydrates': {'percent_min': 2.5,'percent_max': 2.5},
                'water': {'percent_min': 90,'percent_max': 90},
                'sugars': {'percent_min': 0,'percent_max': 0},
                'salt': {'percent_min': 0,'percent_max': 0},
            }
        },
        {
            'id':'en:sugar-and-salt',
            'ingredients': [{
                'id':'en:sugar',
                'nutrients': {
                    'sugars': {'percent_min': 100,'percent_max': 100},
                    'carbohydrates': {'percent_min': 0,'percent_max': 0},
                    'salt': {'percent_min': 0,'percent_max': 0},
                }
            },
            {
                'id':'en:salt',
                'nutrients': {
                    'salt': {'percent_min': 100,'percent_max': 100},
                    'carbohydrates': {'percent_min': 0,'percent_max': 0},
                    'sugars': {'percent_min': 0,'percent_max': 0},
                }
            }
            ]
        }],
        'nutriments': {
            'carbohydrates_100g': 5,
            'sugars_100g': 10,
            'salt_100g': 5
        }}

    estimate_recipe(product)

    # Print the resulting product structure
    print(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    assert metrics['status'] == 0

    sugar = product['ingredients'][1]['ingredients'][0]
    # Percent estimate is relative to total ingredient quantities
    assert round(sugar.get('percent_estimate')) == 5

    # Quantity estimate gives original quantity of ingredient per 100g/ml of product
    assert round(sugar.get('quantity_estimate')) == 10


def test_estimate_recipe_minimize_maximum_distance_between_ingredients():
    product = {
        'ingredients': [
            {
                'id':'one',
                'nutrients': {
                    'carbohydrates': {'percent_min': 15,'percent_max': 15},
                }
            },
            {
                'id':'two',
                'nutrients': {
                    'carbohydrates': {'percent_min': 15,'percent_max': 15},
                }
            },
            {
                'id':'three',
                'nutrients': {
                    'carbohydrates': {'percent_min': 15,'percent_max': 15},
                }
            },
            {
                'id':'four',
                'nutrients': {
                    'carbohydrates': {'percent_min': 15,'percent_max': 15},
                }
            }
        ],
        'nutriments': {
            'carbohydrates_100g': 60,
        }}

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