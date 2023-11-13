from recipe_estimator import estimate_recipe


def test_estimate_recipe_accounts_for_evaporation():
    product = {
        'ingredients': [{
            'id':'en:tomato',
            'nutrients': {
                'carbohydrates': 2.5,
                'water': 90,
            }
        }],
        'nutriments': {
            'carbohydrates': 5,
        }}

    estimate_recipe(product)

    metrics = product.get('recipe_estimator')
    assert metrics is not None

    # Status is valid
    assert metrics['status'] == 0

    ingredient = product['ingredients'][0]
    # Percent estimate is relative to total ingredient quantities
    percent_estimate = ingredient.get('percent_estimate')
    assert percent_estimate > 99
    assert percent_estimate < 101

    # Quantity estimate gives original quantity of ingredient per 100g/ml of product
    quantity_estimate = ingredient.get('quantity_estimate')
    assert quantity_estimate > 199
    assert quantity_estimate < 201

    evaporation = ingredient.get('evaporation')
    assert evaporation > 99
    assert evaporation < 101


