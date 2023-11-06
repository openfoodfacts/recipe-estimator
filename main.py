import itertools
from fastapi import Body, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from ciqual.nutrients import ciqual_ingredients, prepare_product
from product import get_product
from minimize_nutrient_distance import estimate_recipe

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
    return list(itertools.islice(filter(lambda i: (all(search_term in i['alim_nom_eng'].casefold() for search_term in search_terms)), ciqual_ingredients.values()),20))

@app.get("/product/{id}")
async def product(id):
    product = get_product(id)
    return product

@app.post("/recipe")
async def recipe(request: Request):
    product = await request.json()
    if prepare_product(product):
        estimate_recipe(product)
    return product
