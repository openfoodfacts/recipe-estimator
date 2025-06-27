import json
from pathlib import Path
import requests

from . import settings


def print_recipe(ingredients, indent = ''):
    for ingredient in ingredients:
        lost_water = ingredient.get('evaporation', '')
        if type(lost_water) == float:
            lost_water = '(' + str(lost_water) + ')'
        print(indent, '-', ingredient['text'], ingredient['percent_estimate'], lost_water)
        if 'ingredients' in ingredient:
            print_recipe(ingredient['ingredients'], indent + ' ')

def fix_ingredients(ingredients):
    for ingredient in ingredients:
        if 'ingredients' in ingredient:
            sub_ingredients = ingredient['ingredients']
            if (len(sub_ingredients) > 0):
                fix_ingredients(sub_ingredients)
            else:
                del ingredient['ingredients']

def get_product(id):
    # First see if the product is in a test set
    matches = list(Path('../recipe-estimator-metrics/test-sets/input').rglob(id + '.json'))
    if len(matches) > 0:
        with open(matches[0]) as f:
            return json.load(f)

    response = requests.get(settings.OPENFOODFACTS_URL + "/api/v3/product/" + id).json()
    if not 'product' in response:
        return {}

    product = response['product']
    fix_ingredients(product['ingredients'])
    return product

