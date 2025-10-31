from recipe_estimator.nutrients import prepare_product
from .recipe_estimator_simple import estimate_recipe


def test_estimate_recipe_simple_recipe_with_one_unmatched_ingredient():
    product = {
        "code": "test",
        "ingredients": [
            {
                "id": "one",
            },
            {
                "id": "two",
            },
        ],
    }

    estimate_recipe(product)

    metrics = product.get("recipe_estimator")
    assert metrics is not None

    # Status is valid
    # assert metrics['status'] == 0

    assert round(product["ingredients"][0]["percent_estimate"]) >= 50
    assert round(product["ingredients"][1]["percent_estimate"]) <= 50
    assert (
        round(
            product["ingredients"][0]["percent_estimate"]
            + product["ingredients"][1]["percent_estimate"]
        )
        == 100
    )


def test_estimate_recipe_subingredients():
    product = {
        "code": "test",
        "ingredients": [
            {
                "id": "en:tomato",
            },
            {
                "id": "en:sugar-and-salt",
                "ingredients": [
                    {
                        "id": "en:sugar",
                    },
                    {
                        "id": "en:salt",
                    },
                ],
            },
        ],
    }

    estimate_recipe(product)

    # Print the resulting product structure
    # print(json.dumps(product, indent=2))

    metrics = product.get("recipe_estimator")
    assert metrics is not None

    tomatoes = product["ingredients"][0]["percent_estimate"]
    sugar = product["ingredients"][1]["ingredients"][0]["percent_estimate"]
    salt = product["ingredients"][1]["ingredients"][1]["percent_estimate"]
    assert tomatoes > sugar + salt
    assert sugar > salt
    assert abs(100 - (tomatoes + sugar + salt)) < 1
