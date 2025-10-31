from recipe_estimator.bounds import assign_bounds


def test_simple_product():
    ingredients = [
        {},{},{},{}
    ]
    assign_bounds(ingredients)
    assert ingredients[0]['percent_min'] == 25
    assert ingredients[0]['percent_max'] == 100

    assert ingredients[1]['percent_min'] == 0
    assert ingredients[1]['percent_max'] == 50

    assert ingredients[2]['percent_min'] == 0
    assert ingredients[2]['percent_max'] == 33.33

    assert ingredients[3]['percent_min'] == 0
    assert ingredients[3]['percent_max'] == 25

def test_compound_first_ingredient():
    ingredients = [
        {
            "ingredients": [{}, {}]
        },{},{},{}
    ]
    assign_bounds(ingredients)
    assert ingredients[0]['percent_min'] == 25
    assert ingredients[0]['percent_max'] == 100
    assert ingredients[0]['ingredients'][0]['percent_min'] == 12.5
    assert ingredients[0]['ingredients'][0]['percent_max'] == 100
    assert ingredients[0]['ingredients'][1]['percent_min'] == 0
    assert ingredients[0]['ingredients'][1]['percent_max'] == 50

    assert ingredients[1]['percent_min'] == 0
    assert ingredients[1]['percent_max'] == 50

    assert ingredients[2]['percent_min'] == 0
    assert ingredients[2]['percent_max'] == 33.33

    assert ingredients[3]['percent_min'] == 0
    assert ingredients[3]['percent_max'] == 25

# def test_simple_with_known_middle_ingredient():
#     ingredients = [
#         {},{"percent": 20},{}
#     ]
#     assign_bounds(ingredients)
#     assert ingredients[0]['percent_max'] == 80
#     assert ingredients[1]['percent_max'] == 20
#     assert ingredients[2]['percent_max'] == 20

#     assert ingredients[0]['percent_min'] == 33.33
#     assert ingredients[1]['percent_min'] == 20
#     assert ingredients[2]['percent_min'] == 0

# def test_simple_with_known_first_ingredient():
#     ingredients = [
#         {"percent": 60},{},{}
#     ]
#     assign_bounds(ingredients)
#     assert ingredients[0]['percent_max'] == 60
#     assert ingredients[1]['percent_max'] == 40
#     assert ingredients[2]['percent_max'] == 20

#     assert ingredients[0]['percent_min'] == 60
#     assert ingredients[1]['percent_min'] == 20
#     assert ingredients[2]['percent_min'] == 0
