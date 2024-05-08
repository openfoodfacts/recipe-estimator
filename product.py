import requests


def print_recipe(ingredients, indent = ''):
    for ingredient in ingredients:
        lost_water = ingredient.get('evaporation', '')
        if type(lost_water) == float:
            lost_water = '(' + str(lost_water) + ')'
        print(indent, '-', ingredient['text'], ingredient['percent_estimate'], lost_water)
        if 'ingredients' in ingredient:
            print_recipe(ingredient['ingredients'], indent + ' ')


def get_product(id):
    response = requests.get("http://world.openfoodfacts.org/api/v3/product/" + id).json()
    if not 'product' in response:
        return {}

    product = response['product']

    return product

