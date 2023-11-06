import pytest

from ciqual.nutrients import prepare_product

def test_prepare_product():
    product = {'ingredients': [{'id':'en:tomato', 'ciqual_food_code': '20047'}]}
    prepare_product(product)
    nutrients = product['ingredients'][0].get('nutrients')
    assert nutrients is not None
    assert nutrients.get('carbohydrates') is not None

    # Check that units are normalised
    calcium = nutrients.get('calcium')
    assert calcium > 0.006
    assert calcium < 0.010
    