from ciqual.nutrients import off_to_ciqual
import requests

from ciqual.nutrients import setup_ingredients

def prepare_ingredients(ingredients, nutrients):
    count = 0
    for ingredient in ingredients:
        if ('ingredients' in ingredient):
            # Child ingredients
            child_count = prepare_ingredients(ingredient['ingredients'], nutrients)
            if child_count == 0:
                return 0
            count = count + child_count
        else:
            count = count + 1
            ciqual_ingredient = ingredient.get('ciqual_ingredient', None)
            if (ciqual_ingredient is None):
                print('Error: ' + ingredient['text'] + ' has no ciqual ingredient')
                return 0

            ingredient['water_content'] = ciqual_ingredient['Water (g/100g)'] or 0

            ingredient['nutrients'] = {}

            # Eliminate any nutrients where the ingredient has an unknown or missing value
            for nutrient_key in nutrients:
                nutrinet = nutrients[nutrient_key]
                if ('error' in nutrinet):
                    continue

                nutrient_value = ciqual_ingredient.get(nutrient_key,None)
                if nutrient_value is None:
                    nutrinet['error'] = 'Unknown values'
                    continue

                ingredient['nutrients'][nutrient_key] = nutrient_value

                unweighted_total = nutrinet.get('unweighted_total',0)
                nutrinet['unweighted_total'] = unweighted_total + nutrient_value

    return count


def print_recipe(ingredients, indent = ''):
    for ingredient in ingredients:
        lost_water = ingredient.get('evaporation', '')
        if type(lost_water) == float:
            lost_water = '(' + str(lost_water) + ')'
        print(indent, '-', ingredient['text'], ingredient['proportion'], lost_water)
        if 'ingredients' in ingredient:
            print_recipe(ingredient['ingredients'], indent + ' ')


def get_product(id):
    response = requests.get("https://world.openfoodfacts.org/api/v3/product/" + id).json()
    if not 'product' in response:
        return {}

    product = response['product']
    off_ingredients = product['ingredients']
    off_nutrients = product['nutriments']
    #print(product['product_name'])
    #print(product_ingredients)
    #print(product['ingredients_text'])
    #print(off_nutrients)

    nutrients = {}
    for off_nutrient_key in off_nutrients:
        if off_nutrient_key in off_to_ciqual:
            ciqual_nutrient = off_to_ciqual[off_nutrient_key]
            ciqual_unit = ciqual_nutrient['ciqual_unit']
            # Normalise units. OFF units are generally g so need to convert to the
            # Ciqual unit for comparison
            factor = 1.0
            if ciqual_unit == 'mg':
                factor = 1000.0
            elif ciqual_unit == 'µg':
                factor = 1000000.0
            nutrients[ciqual_nutrient['ciqual_id']] = {
                'total': float(off_nutrients[off_nutrient_key]) * factor, 
                'weighting' : float(ciqual_nutrient.get('weighting',1) or 1)
            }
    #print(nutrients)
    ingredients = setup_ingredients(off_ingredients)

    return {'name': product['product_name'], 'ingredients_text': product['ingredients_text'], 'ingredients': ingredients, 'nutrients':nutrients}


def prepare_product(product):
    ingredients = product['ingredients']
    nutrients = product['nutrients']
    count = prepare_ingredients(ingredients, nutrients)

    for nutrient_key in nutrients:
        nutrient = nutrients[nutrient_key]
        if nutrient['total'] == 0 and nutrient['unweighted_total'] == 0:
            nutrient['error'] = 'All zero values'
        else:
            # Weighting based on size of ingredient, i.e. percentage based
            # Comment out this code to use weighting specified in nutrient_map.csv
            if nutrient['total'] > 0:
                nutrient['weighting'] = 1 / nutrient['total']
            else:
                nutrient['weighting'] = min(0.01, count / nutrient['unweighted_total']) # Weighting below 0.01 causes bad performance, although it isn't that simple as just multiplying all weights doesn't help

    # Favor Sodium over salt if both are present
    #if not 'error' in nutrients.get('Sodium (mg/100g)',{}) and not 'error' in nutrients.get('Salt (g/100g)', {}):
    #    nutrients['Salt (g/100g)']['error'] = 'Prefer sodium where both present'

    return count

