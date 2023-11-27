import pytest
from ciqual.nutrients import prepare_product, round_to_n

def test_prepare_product_populates_nutrients():
    product = {'ingredients': [{'id':'en:tomato', 'ciqual_food_code': '20047'}]}
    prepare_product(product)
    
    ingredient_nutrients = product['ingredients'][0].get('nutrients')
    assert ingredient_nutrients is not None
    carbs = ingredient_nutrients.get('carbohydrates')
    assert carbs is not None
    assert carbs['percent_min'] > 2.4
    assert carbs['percent_max'] < 2.6

    # Check that units are normalised
    calcium = ingredient_nutrients.get('calcium')
    assert calcium['percent_min'] > 0.006
    assert calcium['percent_max'] < 0.010

    # Includes water content
    water = ingredient_nutrients.get('water')
    assert water['percent_min'] > 90


def test_prepare_product_looks_up_ciqual_code():
    product = {'ingredients': [{'id':'en:tomato'}]}
    prepare_product(product)
    nutrients = product['ingredients'][0].get('nutrients')
    assert nutrients is not None


def test_prepare_product_creates_a_max_range_entry_if_ingredient_not_found():
    product = {'ingredients': [{'id':'en:does_not_exist'}]};
    prepare_product(product)
    nutrients = product['ingredients'][0].get('nutrients')
    assert nutrients is not None
    fiber = nutrients.get('fiber')
    assert fiber is not None
    assert fiber['percent_min'] >= 0
    assert fiber['percent_max'] <= 80 # Maximum fiber percent on any ingredient is 79%


def test_round_to_n():
    assert round_to_n(1.6666666666, 3) == 1.67
    assert round_to_n(1 / 3, 4) == 0.3333
    assert round_to_n(5 / 3, 4) == 1.667
