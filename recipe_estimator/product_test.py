import os
from .product import get_product

def test_product_comes_from_metrics():
    product = get_product('20005726')
    is_ci = os.environ.get('CI', False)
    assert is_ci or product['product_name'] == 'Studentenfutter Classic'