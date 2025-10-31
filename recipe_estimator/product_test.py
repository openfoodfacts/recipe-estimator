import os
from .product import get_product

def test_product_comes_from_metrics():
    product = get_product('20005726')
    is_ci = os.environ.get('CI', False)
    # Shouldn't see any non-whitelisted fields if came from metrics
    assert is_ci or "_keywords" not in product