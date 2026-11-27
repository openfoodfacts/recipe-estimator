import pytest


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


def test_ingredients_sum_to_at_least_100():
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
                    'fiber': {'percent_nom': 10, 'percent_min': 10, 'percent_max': 10},
                }
            }
        ],
        'nutriments': {
            'fiber_100g': 10,
        }}

    estimate_recipe(product)

    total_quantity = sum(ingredient['quantity_estimate'] for ingredient in product['ingredients'])
    assert total_quantity >= 100

    # percent_estimate is the share in the recipe, so it sums to 100% even if more than 100 g of ingredients are used
    total_percent = sum(ingredient['percent_estimate'] for ingredient in product['ingredients'])
    assert abs(total_percent - 100) < 0.1


def test_specified_percent_is_kept_as_recipe_share_with_evaporation():
    # Crisps-like product: potatoes (80% water) fried in oil, most of the water evaporates.
    # The label says potatoes 62%: it is the share of potatoes in the recipe, so percent_estimate
    # must be 62% even if more than 100 g of ingredients are used for 100 g of product
    product = {
        'code': 'test',
        'ingredients': [
            {
                'id': 'en:potato',
                'percent': 62,
                'nutrients': {
                    'water': {'percent_nom': 80, 'percent_min': 80, 'percent_max': 80},
                    'carbohydrates': {'percent_nom': 18, 'percent_min': 18, 'percent_max': 18},
                    'fat': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                }
            },
            {
                'id': 'en:sunflower-oil',
                'nutrients': {
                    'water': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                    'carbohydrates': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                    'fat': {'percent_nom': 100, 'percent_min': 100, 'percent_max': 100},
                }
            }
        ],
        'nutriments': {
            'carbohydrates_100g': 50,
            'fat_100g': 35,
        }}

    estimate_recipe(product)

    potato, oil = product['ingredients']
    assert abs(potato['percent_estimate'] - 62) <= 0.5
    assert abs(potato['percent_estimate'] + oil['percent_estimate'] - 100) < 0.1
    # Water was lost after the mixing bowl
    assert potato['quantity_estimate'] + oil['quantity_estimate'] > 100


def test_specified_percents_over_100_are_quantities_for_100g_of_product():
    # Dried sausage: "pork 140%" can only be the quantity of pork used for 100 g of product
    # (EU regulation 1169/2011 Annex VIII point 4(a))
    product = {
        'code': 'test',
        'ingredients': [
            {
                'id': 'en:pork',
                'percent': 140,
                'nutrients': {
                    'water': {'percent_nom': 60, 'percent_min': 60, 'percent_max': 60},
                    'proteins': {'percent_nom': 20, 'percent_min': 20, 'percent_max': 20},
                    'fat': {'percent_nom': 20, 'percent_min': 20, 'percent_max': 20},
                }
            },
            {
                'id': 'en:salt',
                'nutrients': {
                    'salt': {'percent_nom': 100, 'percent_min': 100, 'percent_max': 100},
                }
            }
        ],
        'nutriments': {
            'proteins_100g': 28,
            'fat_100g': 28,
            'salt_100g': 4,
        }}

    estimate_recipe(product)

    pork = product['ingredients'][0]
    assert abs(pork['quantity_estimate'] - 140) <= 0.5
    assert abs(sum(ingredient['percent_estimate'] for ingredient in product['ingredients']) - 100) < 0.1


def test_ingredients_after_an_ingredient_under_2_percent_can_be_in_any_order():
    # "A 96%, B 1%, C": C is after B but can be bigger than B, as ingredients under 2% can be listed in any order.
    # With the order constraint (C <= B), the specified percents could not sum to 100%
    def ingredient(id, percent, fiber):
        ingredient = {
            'id': id,
            'nutrients': {
                'water': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                'fiber': {'percent_nom': fiber, 'percent_min': fiber, 'percent_max': fiber},
            }
        }
        if percent is not None:
            ingredient['percent'] = percent
        return ingredient

    product = {
        'code': 'test',
        'ingredients': [ingredient('A', 96, 0), ingredient('B', 1, 0), ingredient('C', None, 100)],
        'nutriments': {
            'fiber_100g': 2.5,
        }}

    estimate_recipe(product)

    a, b, c = product['ingredients']
    assert product['recipe_estimator']['specified_percents_basis'] == 'recipe_share'
    assert abs(a['percent_estimate'] - 96) <= 0.5
    assert abs(b['percent_estimate'] - 1) <= 0.5
    assert c['percent_estimate'] > b['percent_estimate']
    assert c['percent_estimate'] <= 2.01


def test_sub_ingredients_of_an_ingredient_under_2_percent_can_be_in_any_order():
    # "A 99%, B 1% (B1, B2)": B1 and B2 are under 2% of the product, so B2 can be bigger than B1
    def ingredient(id, fiber, percent=None):
        ingredient = {
            'id': id,
            'nutrients': {
                'water': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
                'fiber': {'percent_nom': fiber, 'percent_min': fiber, 'percent_max': fiber},
            }
        }
        if percent is not None:
            ingredient['percent'] = percent
        return ingredient

    b = {'id': 'B', 'percent': 1, 'ingredients': [ingredient('B1', 0), ingredient('B2', 100)]}
    product = {
        'code': 'test',
        'ingredients': [ingredient('A', 0, 99), b],
        'nutriments': {
            'fiber_100g': 0.8,
        }}

    estimate_recipe(product)

    b1, b2 = product['ingredients'][1]['ingredients']
    assert b2['percent_estimate'] > b1['percent_estimate']
    assert abs(b2['percent_estimate'] - 0.8) <= 0.1


def fiber_ingredient(id, fiber, percent=None):
    ingredient = {
        'id': id,
        'nutrients': {
            'water': {'percent_nom': 0, 'percent_min': 0, 'percent_max': 0},
            'fiber': {'percent_nom': fiber, 'percent_min': fiber, 'percent_max': fiber},
        }
    }
    if percent is not None:
        ingredient['percent'] = percent
    return ingredient


@pytest.mark.parametrize('ingredient_id, quantity_max', [
    ('en:lactic-ferments', 1),  # ferments
    ('en:e202', 0.5),  # preservative E-number
    ('en:preservative', 0.5),  # additive class without E-number
    ('en:flavouring', 5),  # percent_max:en in the ingredients taxonomy
    ('en:e965', None),  # maltitol: polyols can be used in large quantities
])
def test_quantity_max_of_additives_and_ferments(ingredient_id, quantity_max):
    # The nutrients would give 40 g of the second ingredient, unless it has a maximum quantity
    product = {
        'code': 'test',
        'ingredients': [fiber_ingredient('A', 0), fiber_ingredient(ingredient_id, 100)],
        'nutriments': {
            'fiber_100g': 40,
        }}

    estimate_recipe(product)

    quantity_estimate = product['ingredients'][1]['quantity_estimate']
    if quantity_max is None:
        assert abs(quantity_estimate - 40) < 1
    else:
        assert quantity_estimate <= quantity_max + 0.01
    assert 'skipped_quantity_max' not in product['recipe_estimator']


def test_quantity_max_does_not_apply_to_the_first_ingredient():
    product = {
        'code': 'test',
        'ingredients': [fiber_ingredient('en:lactic-ferments', 100), fiber_ingredient('A', 0)],
        'nutriments': {
            'fiber_100g': 60,
        }}

    estimate_recipe(product)

    assert abs(product['ingredients'][0]['quantity_estimate'] - 60) < 1


def test_quantity_max_is_skipped_if_infeasible_with_the_label():
    # "A, preservative, B 10%": the preservative is listed before B, so it is at least 10%
    product = {
        'code': 'test',
        'ingredients': [fiber_ingredient('A', 0), fiber_ingredient('en:preservative', 0), fiber_ingredient('B', 0, 10)],
        'nutriments': {
            'fiber_100g': 0,
        }}

    estimate_recipe(product)

    a, preservative, b = product['ingredients']
    assert product['recipe_estimator']['skipped_quantity_max'] == ['en:preservative']
    assert abs(b['percent_estimate'] - 10) <= 0.5
    assert preservative['percent_estimate'] >= b['percent_estimate'] - 0.01
