from .nutrients import get_ciqual_code, prepare_product

def test_prepare_product_populates_nutrients():
    product = {
        'code' : 1234567890123,
        'ingredients': [{'id':'en:tomato', 'ciqual_food_code': '20047'}],
    }
    prepare_product(product)

    ingredient_nutrients = product['ingredients'][0].get('nutrients')
    assert ingredient_nutrients is not None
    carbs = ingredient_nutrients.get('carbohydrates')
    assert carbs is not None
    assert carbs['percent_min'] > 2.4
    assert 2.6 < carbs['percent_max'] < 5.2

    # Check that units are normalised
    calcium = ingredient_nutrients.get('calcium')
    assert 0.001 < calcium['percent_min'] < 0.006
    assert 0.010 < calcium['percent_max'] < 0.020

    # Includes water content
    water = ingredient_nutrients.get('water')
    assert 80 < water['percent_min'] < 90

def test_prepare_product_looks_up_ciqual_code():
    product = {'ingredients': [{'id':'en:tomato'}]}
    prepare_product(product)
    nutrients = product['ingredients'][0].get('nutrients')
    assert nutrients is not None


def test_prepare_product_creates_a_max_range_entry_if_ingredient_not_found():
    product = {
        'code' : 1234567890123,
        'ingredients': [{'id':'en:does_not_exist'}],
    }
    prepare_product(product)
    nutrients = product['ingredients'][0].get('nutrients')
    assert nutrients is not None
    carbs = nutrients.get('carbohydrates')
    assert carbs is not None
    assert carbs['percent_min'] >= 0
    assert carbs['percent_max'] <= 100

def test_prepare_product_adds_up_sugars_if_not_specified():
    product = {'code' : 1234567890123, 'ingredients': [{'id':'en:fructose'}]}
    prepare_product(product)
    nutrients = product['ingredients'][0].get('nutrients')
    assert nutrients is not None
    sugars = nutrients.get('sugars')
    assert sugars is not None
    assert sugars['percent_min'] >= 90
    assert sugars['percent_max'] <= 100

def test_get_ciqual_code_should_use_proxy_if_no_main_code():
    ciqual_code, ciqual_proxy_code = get_ciqual_code('en:tomato-sauce')
    assert ciqual_code is None
    assert ciqual_proxy_code == '11107'
