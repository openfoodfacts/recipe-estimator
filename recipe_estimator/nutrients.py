import json
import os

from .nutrient_map import off_to_ciqual

# Load ciqual ingredients
with open(os.path.join(os.path.dirname(__file__), "assets/ciqual_ingredients.json"), "r", encoding="utf-8") as ciqual_file:
    ciqual_ingredients = json.load(ciqual_file)

# Load ingredients
with open(os.path.join(os.path.dirname(__file__), "assets/ingredients.json"), "r", encoding="utf-8") as ingredients_file:
    ingredients_taxonomy = json.load(ingredients_file)

def get_ciqual_code(ingredient_id):
    ciqual_code = None
    ciqual_proxy_code = None
    
    ingredient = ingredients_taxonomy.get(ingredient_id, None)
    if ingredient is None:
        print(ingredient_id + ' not found')       
        return None, None

    ciqual_code_object = ingredient.get('ciqual_food_code', None)
    if ciqual_code_object:
        ciqual_code  = ciqual_code_object['en']
    ciqual_code_object = ingredient.get('ciqual_proxy_food_code', None)
    if ciqual_code_object:
        ciqual_proxy_code = ciqual_code_object['en']

    if not ciqual_code and not ciqual_proxy_code:
        parents = ingredient.get('parents', None)
        if parents:
            for parent_id in parents:
                ciqual_code, ciqual_proxy_code = get_ciqual_code(parent_id)
                if ciqual_code or ciqual_proxy_code:
                    print(f"Obtained ciqual_code for {ingredient_id} from parent {parent_id}")
                    break

    return ciqual_code, ciqual_proxy_code


def setup_ingredients(ingredients, nutrients):
    for ingredient in ingredients:
        if ('ingredients' in ingredient and len(ingredient['ingredients']) > 0):
            # Child ingredients
            setup_ingredients(ingredient['ingredients'], nutrients)

        else:
            # Always get the ciqual code from the taxonomy unless the nutrients are already setup
            if 'nutrients' not in ingredient:
                ciqual_code, ciqual_proxy_code = get_ciqual_code(ingredient['id'])
                ingredient['ciqual_food_code'] = ciqual_code
                ingredient['ciqual_proxy_food_code'] = ciqual_proxy_code
                
                ciqual_code = ciqual_code or ciqual_proxy_code

                # Convert CIQUAL nutrient codes back to OFF
                ingredient_nutrients = {}
                ciqual_ingredient = ciqual_ingredients.get(ciqual_code, None)
                if (ciqual_ingredient is None):
                    # Invent a dummy set of nutrients with maximum ranges
                    # TODO: Could use value ranges that occur in actual data
                    ingredient['alim_nom_eng'] = 'Unknown'
                    for off_id in off_to_ciqual:
                        ingredient_nutrients[off_id] = {'percent_min': 0, 'percent_nom': 0, 'percent_max': 0, 'confidence': '-'}
                else:
                    ingredient['alim_nom_eng'] = ciqual_ingredient['alim_nom_eng']
                    ingredient_nutrients = ciqual_ingredient['nutrients']

                ingredient['nutrients'] = ingredient_nutrients
                ingredient['ciqual_food_code_used'] = ciqual_code


def prepare_product(product):
    setup_ingredients(product['ingredients'], product.get('nutriments', {}))



# Dump ingredients
#with open(filename, "w", encoding="utf-8") as ingredients_file:
#    json.dump(
#        ingredients, ingredients_file, sort_keys=True, indent=4, ensure_ascii=False
#    )
