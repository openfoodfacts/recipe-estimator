import itertools
from fastapi import Body, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .nutrients import ciqual_ingredients, prepare_product
from .product import get_product
from .recipe_estimator import estimate_recipe
from .recipe_estimator_scipy import estimate_recipe as estimate_recipe_scipy, get_objective_function_args, objective

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

@app.post("/api/v3/estimate_recipe")
async def recipe(request: Request):
    product = await request.json()
    prepare_product(product)
    estimate_recipe(product)
    return product

@app.post("/api/v3/estimate_recipe_scipy")
async def recipe(request: Request):
    product = await request.json()
    prepare_product(product)
    estimate_recipe_scipy(product)
    return product

@app.post("/api/v3/get_penalties")
async def recipe(request: Request):
    product = await request.json()
    prepare_product(product)
    [_, leaf_ingredients, args] = get_objective_function_args(product)
    quantities = [float(ingredient['quantity_estimate']) for ingredient in leaf_ingredients]
    objective(quantities, *args)
    product['recipe_estimator']['penalties'] = args[0]
    return product
