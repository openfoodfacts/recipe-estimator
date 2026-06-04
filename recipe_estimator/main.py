import itertools
from json import JSONDecodeError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from .nutrients import ciqual_ingredients, prepare_product, remove_temporary_ingredients_fields
from .product import get_product
from .recipe_estimator import estimate_recipe
from .recipe_estimator_scipy import estimate_recipe as estimate_recipe_scipy
from .recipe_estimator_nnls import estimate_recipe as estimate_recipe_nnls
from .recipe_estimator_unconstrained_nnls import estimate_recipe as estimate_recipe_unconstrained_nnls
from .recipe_estimator_simple import estimate_recipe as estimate_recipe_simple
from .recipe_estimator_po import estimate_recipe as estimate_recipe_po
from .recipe_estimator_cvxpy import estimate_recipe as estimate_recipe_cvxpy
from .fitness import get_objective_function_args, objective

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="./static",html=True), name="static")

@app.get("/")
async def redirect():
    return RedirectResponse("static")

@app.get("/ciqual/{name}")
async def ciqual(name):
    search_terms = name.casefold().split()
    return list(itertools.islice(filter(lambda i: (all(search_term in (i['alim_nom_eng'] + i['ciqual_food_code']).casefold() for search_term in search_terms)), ciqual_ingredients.values()),20))

@app.get("/product/{id}")
async def product(id):
    product = get_product(id)
    return product


def _issue(field_id, impact_id, impact_name, message_id, message_name):
    return {
        "field": {"id": field_id},
        "impact": {
            "id": impact_id,
            "lc_name": impact_name,
            "name": impact_name,
        },
        "message": {
            "id": message_id,
            "lc_name": message_name,
            "name": message_name,
        },
    }


def add_error(errors, field_id, message_id, message_name, impact_id="failure", impact_name="Failure"):
    errors.append(_issue(field_id, impact_id, impact_name, message_id, message_name))


def add_warning(warnings, field_id, message_id, message_name, impact_id="warning", impact_name="Warning"):
    warnings.append(_issue(field_id, impact_id, impact_name, message_id, message_name))


def _failure_response(errors, warnings, status_code=400):
    return JSONResponse(
        status_code=status_code,
        content={
            "errors": errors,
            "status": "failure",
            "warnings": warnings,
        },
    )


async def _read_product(request: Request):
    errors = []
    warnings = []
    try:
        payload = await request.json()
    except JSONDecodeError:
        add_error(errors, "body", "invalid_json", "Invalid JSON")
        return None, {}, _failure_response(errors, warnings)

    if not isinstance(payload, dict):
        add_error(errors, "body", "invalid_json", "Invalid JSON")
        return None, {}, _failure_response(errors, warnings)

    if "product" not in payload:
        add_error(errors, "product", "missing_field", "Missing field")
        return None, {}, _failure_response(errors, warnings)

    if not isinstance(payload["product"], dict):
        add_error(errors, "product", "invalid_type", "Invalid type")
        return None, {}, _failure_response(errors, warnings)

    options = payload.get("options", {})
    if not isinstance(options, dict):
        options = {}

    return payload["product"], options, None


def _product_response(product, options=None):
    debug = bool((options or {}).get("debug"))
    if not debug:
        remove_temporary_ingredients_fields(product.get("ingredients", []))
    return {"product": product}

# /estimate_recipe uses the default recipe estimation method (currently cvxpy)
@app.post("/api/v3/estimate_recipe")
async def recipe(request: Request):
    product, options, error_response = await _read_product(request)
    if error_response:
        return error_response
    prepare_product(product)
    estimate_recipe_cvxpy(product)
    return _product_response(product, options)
    
@app.post("/api/v3/estimate_recipe_glop")
async def recipe(request: Request):
    product, options, error_response = await _read_product(request)
    if error_response:
        return error_response
    prepare_product(product)
    estimate_recipe_cvxpy(product)
    return product

@app.post("/api/v3/estimate_recipe_glop")
async def recipe(request: Request):
    product = await request.json()
    prepare_product(product)
    estimate_recipe(product)
    return _product_response(product, options)

@app.post("/api/v3/estimate_recipe_scipy")
async def recipe(request: Request):
    product, options, error_response = await _read_product(request)
    if error_response:
        return error_response
    prepare_product(product)
    estimate_recipe_scipy(product)
    return _product_response(product, options)

@app.post("/api/v3/estimate_recipe_nnls")
async def recipe(request: Request):
    product, options, error_response = await _read_product(request)
    if error_response:
        return error_response
    prepare_product(product)
    estimate_recipe_nnls(product)
    return _product_response(product, options)

@app.post("/api/v3/unconstrained_nnls")
async def recipe(request: Request):
    payload = await request.json()
    product = payload.get("product") if isinstance(payload, dict) and "product" in payload else payload
    options = payload.get("options", {}) if isinstance(payload, dict) else {}
    if not isinstance(options, dict):
        options = {}
    prepare_product(product)
    estimate_recipe_unconstrained_nnls(product)
    if not bool(options.get("debug")):
        remove_temporary_ingredients_fields(product.get("ingredients", []))
    return product

@app.post("/api/v3/estimate_recipe_simple")
async def recipe(request: Request):
    product, options, error_response = await _read_product(request)
    if error_response:
        return error_response
    prepare_product(product)
    estimate_recipe_simple(product)
    return _product_response(product, options)

@app.post("/api/v3/estimate_recipe_po")
async def recipe(request: Request):
    product, options, error_response = await _read_product(request)
    if error_response:
        return error_response
    prepare_product(product)
    estimate_recipe_po(product)
    return _product_response(product, options)

@app.post("/api/v3/estimate_recipe_cvxpy")
async def recipe(request: Request):
    product, options, error_response = await _read_product(request)
    if error_response:
        return error_response
    prepare_product(product)
    estimate_recipe_cvxpy(product)
    return _product_response(product, options)

@app.post("/api/v3/get_penalties")
async def recipe(request: Request):
    product = await request.json()
    prepare_product(product)
    [_, leaf_ingredients, args] = get_objective_function_args(product)
    quantities = np.array([float(ingredient['quantity_estimate']) for ingredient in leaf_ingredients])
    objective(quantities, *args)
    product['recipe_estimator']['penalties'] = args[0]
    return product
