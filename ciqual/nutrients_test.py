import pytest
from ciqual.nutrients import prepare_product

def test_prepare_product_populates_nutrients():
    product = {'ingredients': [{'id':'en:tomato', 'ciqual_food_code': '20047'}]}
    prepare_product(product)
    
    ingredient_nutrients = product['ingredients'][0].get('nutrients')
    assert ingredient_nutrients is not None
    assert ingredient_nutrients.get('carbohydrates') is not None

    # Check that units are normalised
    calcium = ingredient_nutrients.get('calcium')
    assert calcium > 0.006
    assert calcium < 0.010

    # The basic list of nutrients should be created
    nutrients = product['recipe_estimator']['nutrients']
    carbs = nutrients.get('carbohydrates')
    assert carbs.get('ciqual_nutient_code') == 'Carbohydrate (g/100g)'
    assert carbs.get('conversion_factor') == 1
    assert carbs.get('ingredient_count') == 1

    assert product['recipe_estimator']['metrics']['ingredient_count'] == 1


def test_prepare_product_looks_up_ciqual_code():
    product = {'ingredients': [{'id':'en:tomato'}]}
    prepare_product(product)
    nutrients = product['ingredients'][0].get('nutrients')
    assert nutrients is not None


def test_prepare_product_raises_exception_if_ingredient_not_found():
    with pytest.raises(Exception, match=r'.*en:does_not_exist.*'):
        prepare_product({'ingredients': [{'id':'en:does_not_exist'}]})

