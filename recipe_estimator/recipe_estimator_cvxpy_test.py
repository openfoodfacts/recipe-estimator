
import json
import os
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

def test_estimate_recipe_salty_snacks_water_loss():
    # Simulate a fried product (e.g., crisps) to ensure the mass penalty 
    # doesn't cause a solver plateau or zero out exact micro-ingredients.
    product = {
        'code': 'crisps_test',
        'categories_tags': ['en:salty-snacks', 'en:crisps'],
        'ingredients': [
            {
                'id': 'en:potato',
                'nutrients': {
                    'carbohydrates': {'percent_nom': 17, 'percent_min': 15, 'percent_max': 19},
                    'water': {'percent_nom': 77, 'percent_min': 75, 'percent_max': 80}
                }
            },
            {
                'id': 'en:sunflower-oil',
                'nutrients': {
                    'fat': {'percent_nom': 100, 'percent_min': 100, 'percent_max': 100},
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
            'carbohydrates_100g': 51,
            'fat_100g': 32,
            'salt_100g': 1.2
        },
        'recipe_estimator': {
            'nutrients': {
                'carbohydrates': {'product_total': 51, 'weighting': 1},
                'fat': {'product_total': 32, 'weighting': 1},
                'salt': {'product_total': 1.2, 'weighting': 1}
            }
        }
    }

    estimate_recipe(product)
    
    potato = product['ingredients'][0]
    oil = product['ingredients'][1]
    salt = product['ingredients'][2]
    
    # Raw potato mass should be > 200% to account for evaporation
    assert potato.get('percent_estimate', 0) > 200
    
    # Oil estimate should closely match the total fat content
    assert abs(32 - oil.get('percent_estimate', 0)) < 5
    
    # Salt must not be zeroed out by the mass constraints
    # Note: Even a partial estimation > 0.5 proves the plateau is broken
    assert salt.get('percent_estimate', 0) >= 0.5


def load_crisps_test_data():
    """Load test data from crisps_test_set.json"""
    test_data_dir = os.path.dirname(__file__)
    test_data_path = os.path.join(test_data_dir, 'test_data', 'crisps_test_set.json')
    
    if not os.path.exists(test_data_path):
        pytest.skip(f"Test data file not found: {test_data_path}")
    
    with open(test_data_path, 'r') as f:
        return json.load(f)


# Load test data for parametrized tests
try:
    CRISPS_TEST_DATA = load_crisps_test_data()
except:
    CRISPS_TEST_DATA = []


@pytest.mark.parametrize("product_data", CRISPS_TEST_DATA, ids=lambda p: p.get('_id', 'unknown'))
def test_estimate_recipe_from_crisps_dataset(product_data):
    """Test recipe estimation on real-world crisp products from OpenFoodFacts"""
    # Prepare product for estimation
    product = {
        'code': product_data['_id'],
        'categories_tags': product_data.get('categories_tags', []),
        'ingredients': product_data.get('ingredients', []),
        'nutriments': product_data.get('nutriments', {})
    }
    
    # Run estimation
    estimate_recipe(product)
    
    # Basic validation - check that we have results
    metrics = product.get('recipe_estimator')
    assert metrics is not None, f"No recipe_estimator metrics for {product_data['product_name']}"
    
    # Check that all ingredients have percent estimates
    for ingredient in product.get('ingredients', []):
        percent = ingredient.get('percent_estimate')
        assert percent is not None, f"Missing percent_estimate for ingredient {ingredient['id']} in {product_data['product_name']}"
        assert percent >= 0, f"Ingredient {ingredient['id']} has zero/negative estimate in {product_data['product_name']}"
    
    # For high-water-loss products (fried snacks), verify reasonable estimates
    categories = product_data.get('categories_tags', [])
    is_fried = any(cat in categories for cat in ['en:salty-snacks', 'en:crisps', 'en:potato-crisps', 'en:chips-and-fries', 'en:corn-chips'])
    
    if is_fried:
        # Total ingredient mass should be > 100 to account for water loss
        total_mass = sum(ing.get('percent_estimate', 0) for ing in product['ingredients'])
        assert total_mass > 100, f"Total ingredient mass too low ({total_mass}) for fried product {product_data['product_name']}"

    