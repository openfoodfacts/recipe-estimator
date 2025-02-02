import csv
import json
import os
import xml.etree.ElementTree as ET

def parse_value(ciqual_nutrient):
    if not ciqual_nutrient or ciqual_nutrient == '-':
        return 0
    return float(ciqual_nutrient.replace(',','.').replace('<','').replace('traces','0'))

const_codes = {}
const_table = ET.parse(os.path.join(os.path.dirname(__file__), "const_2020_07_07.xml")).getroot()
for const in const_table:
    const_codes[const.find('const_nom_eng').text.strip()] = const.find('const_code').text.strip()

# Load OFF Ciqual Nutrient mapping
off_to_ciqual = {}
ciqual_to_off = {}
filename = os.path.join(os.path.dirname(__file__), "nutrient_map.csv")
with open(filename, newline="", encoding="utf8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if row["ciqual_id"]:
            # Normalise units. OFF units are generally g so need to convert to the
            # Ciqual unit for comparison
            factor = 1.0
            ciqual_unit = row['ciqual_unit']
            if ciqual_unit == 'mg':
                factor = 1000.0
            elif ciqual_unit == 'µg':
                factor = 1000000.0
            row['factor'] = factor
            off_to_ciqual[row["off_id"]] = row
            ciqual_to_off[const_codes[row["ciqual_id"]]] = row

# Load Ciqual data
alim_codes = {}
alim_table = ET.parse(os.path.join(os.path.dirname(__file__), "alim_2020_07_07.xml")).getroot()
for alim in alim_table:
    alim_codes[alim.find('alim_code').text.strip()] = alim.find('alim_nom_eng').text.strip()

ciqual_ingredients = {}

# Compo file is not valid XML. Need to fix all of the "less than" entries
with open(os.path.join(os.path.dirname(__file__), "compo_2020_07_07.xml"), encoding="utf8") as compo_file:
    compo_table = ET.fromstring(compo_file.read().replace(' < ', ' &lt; '))

for compo in compo_table:
    const_code = compo.find('const_code').text.strip()
    nutrient = ciqual_to_off.get(const_code)
    if nutrient is not None:
        nutrient_key = nutrient['off_id']
        factor = nutrient['factor']
        alim_code = compo.find('alim_code').text.strip()
        teneur = compo.find('teneur').text.strip()
        min = compo.find('min').text
        max = compo.find('max').text
        nom_value = parse_value(teneur)

        # TODO: If min and max not set then should be able to apply tolerance based on code_confiance
        if min is not None:
            min_value = parse_value(min.strip())
        elif '<' in teneur:
            min_value = 0
        else:
            min_value = nom_value

        if max is not None:
            max_value = parse_value(max.strip())
        else:
            max_value = nom_value

        ciqual_ingredient = ciqual_ingredients.setdefault(alim_code, {
            'id': alim_code,
            'ciqual_food_code': alim_code,
            'alim_nom_eng': alim_codes[alim_code],
            'text': alim_codes[alim_code],
            'nutrients': {},
        })
        ciqual_ingredient = ciqual_ingredients.get(alim_code, {})
        ciqual_ingredient['nutrients'][nutrient_key] = {
            'percent_nom': nom_value / factor,
            'percent_min': min_value / factor,
            'percent_max': max_value / factor,
        }

# Load ingredients
filename = os.path.join(os.path.dirname(__file__), "ingredients.json")
with open(filename, "r", encoding="utf-8") as ingredients_file:
    ingredients_taxonomy = json.load(ingredients_file)

def get_ciqual_code(ingredient_id):
    ingredient = ingredients_taxonomy.get(ingredient_id, None)
    if ingredient is None:
        print(ingredient_id + ' not found')        
        return None

    ciqual_code = ingredient.get('ciqual_food_code', ingredient.get('ciqual_proxy_food_code', None))
    if ciqual_code:
        return ciqual_code['en']

    parents = ingredient.get('parents', None)
    if parents:
        for parent_id in parents:
            ciqual_code = get_ciqual_code(parent_id)
            if ciqual_code:
                print('Obtained ciqual_code from ' + parent_id)
                return ciqual_code

    return None


def setup_ingredients(ingredients, nutrients):
    for ingredient in ingredients:
        if ('ingredients' in ingredient and len(ingredient['ingredients']) > 0):
            # Child ingredients
            setup_ingredients(ingredient['ingredients'], nutrients)

        else:
            ciqual_code = ingredient.get('ciqual_food_code', ingredient.get('ciqual_proxy_food_code', None))
            if (ciqual_code is None):
                ciqual_code = get_ciqual_code(ingredient['id'])

            # Convert CIQUAL nutrient codes back to OFF
            ingredient_nutrients = {}
            ciqual_ingredient = ciqual_ingredients.get(ciqual_code, None)
            if (ciqual_ingredient is None):
                # Invent a dummy set of nutrients with maximum ranges
                # TODO: Could use max values that occur in actual data
                for off_id in off_to_ciqual:
                    product_nutrient_value = nutrients.get(off_id + '_100g', 0)
                    # using the average product nutrient values for unknown ingredients does not give good results      
                    # ingredient_nutrients[off_id] = {'percent_min': product_nutrient_value, 'percent_max': product_nutrient_value}
                    # set the nutrient contribution from unknown ingredients to 0
                    ingredient_nutrients[off_id] = {'percent_min': 0, 'percent_nom': 0, 'percent_max': 0}
            else:
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
