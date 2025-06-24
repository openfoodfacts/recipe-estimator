from .product import get_product

def test_product_comes_from_metrics():
    product = get_product('20005726')
    assert product['product_name'] == 'Studentenfutter Classic'