import pytest
from fastapi.testclient import TestClient

from .main import app
from .nutrients import prepare_product
from .product import get_product
from .recipe_estimator_scipy import estimate_recipe as estimate_recipe_scipy


ESTIMATE_RECIPE_ENDPOINTS = [
    "/api/v3/estimate_recipe",
    "/api/v3/estimate_recipe_glop",
    "/api/v3/estimate_recipe_scipy",
    "/api/v3/estimate_recipe_nnls",
    "/api/v3/estimate_recipe_simple",
    "/api/v3/estimate_recipe_po",
    "/api/v3/estimate_recipe_cvxpy",
]


@pytest.mark.parametrize("endpoint", ESTIMATE_RECIPE_ENDPOINTS)
def test_estimate_recipe_requires_valid_json_body(endpoint):
    client = TestClient(app)
    response = client.post(
        endpoint,
        data="not-a-json-payload",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "field": {"id": "body"},
                "impact": {
                    "id": "failure",
                    "lc_name": "Failure",
                    "name": "Failure",
                },
                "message": {
                    "id": "invalid_json",
                    "lc_name": "Invalid JSON",
                    "name": "Invalid JSON",
                },
            }
        ],
        "status": "failure",
        "warnings": [],
    }


@pytest.mark.parametrize("endpoint", ESTIMATE_RECIPE_ENDPOINTS)
def test_estimate_recipe_requires_product_object(endpoint):
    client = TestClient(app)
    response = client.post(endpoint, json={})

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "field": {"id": "product"},
                "impact": {
                    "id": "failure",
                    "lc_name": "Failure",
                    "name": "Failure",
                },
                "message": {
                    "id": "missing_field",
                    "lc_name": "Missing field",
                    "name": "Missing field",
                },
            }
        ],
        "status": "failure",
        "warnings": [],
    }


@pytest.mark.parametrize("endpoint", ESTIMATE_RECIPE_ENDPOINTS)
def test_estimate_recipe_requires_product_to_be_object(endpoint):
    client = TestClient(app)
    response = client.post(endpoint, json={"product": "invalid"})

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "field": {"id": "product"},
                "impact": {
                    "id": "failure",
                    "lc_name": "Failure",
                    "name": "Failure",
                },
                "message": {
                    "id": "invalid_type",
                    "lc_name": "Invalid type",
                    "name": "Invalid type",
                },
            }
        ],
        "status": "failure",
        "warnings": [],
    }


@pytest.mark.parametrize("endpoint", ESTIMATE_RECIPE_ENDPOINTS)
def test_estimate_recipe_removes_temporary_ingredient_fields(endpoint):
    client = TestClient(app)
    payload = {
        "product": {
            "ingredients": [
                {
                    "id": "en:sugar",
                    "ingredients": [{"id": "en:water"}],
                }
            ]
        }
    }

    response = client.post(endpoint, json=payload)

    assert response.status_code == 200
    parent = response.json()["product"]["ingredients"][0]
    child = parent["ingredients"][0]
    assert "ciqual_food_code_used" not in child
    assert "nutrients" not in child


@pytest.mark.parametrize("endpoint", ESTIMATE_RECIPE_ENDPOINTS)
def test_estimate_recipe_keeps_temporary_ingredient_fields_with_debug(endpoint):
    client = TestClient(app)
    payload = {
        "product": {
            "ingredients": [
                {
                    "id": "en:sugar",
                    "ingredients": [{"id": "en:water"}],
                }
            ]
        },
        "options": {"debug": True},
    }

    response = client.post(endpoint, json=payload)

    assert response.status_code == 200
    parent = response.json()["product"]["ingredients"][0]
    child = parent["ingredients"][0]
    assert "ciqual_food_code_used" in child
    assert "nutrients" in child

@pytest.mark.slow
def test_estimate_recipe():
    product = get_product("20023751")
    prepare_product(product)
    estimate_recipe_scipy(product)
    assert product["recipe_estimator"]


print(__name__)
if __name__ == "__main__":
    test_estimate_recipe()
