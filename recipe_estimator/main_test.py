import pytest
from .nutrients import prepare_product
from .product import get_product
from .recipe_estimator_scipy import estimate_recipe as estimate_recipe_scipy


@pytest.mark.slow
def test_estimate_recipe():
    product = get_product("20023751")
    prepare_product(product)
    estimate_recipe_scipy(product)
    assert product["recipe_estimator"]


print(__name__)
if __name__ == "__main__":
    test_estimate_recipe()
