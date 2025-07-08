import csv
import json
import os
import xml.etree.ElementTree as ET

def parse_value(ciqual_nutrient):
    if not ciqual_nutrient or ciqual_nutrient == '-':
        return 0
    return float(ciqual_nutrient.replace(',','.').replace('<','').replace('traces','0'))

const_codes = {}
const_table = ET.parse(os.path.join(os.path.dirname(__file__), "assets/ciqual/const_2020_07_07.xml")).getroot()
for const in const_table:
    const_codes[const.find('const_nom_eng').text.strip()] = const.find('const_code').text.strip()

# Load OFF Ciqual Nutrient mapping
off_to_ciqual = {}
ciqual_to_off = {}
filename = os.path.join(os.path.dirname(__file__), "assets/taxonomies/nutrient_map.csv")
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
alim_table = ET.parse(os.path.join(os.path.dirname(__file__), "assets/ciqual/alim_2020_07_07.xml")).getroot()
for alim in alim_table:
    alim_codes[alim.find('alim_code').text.strip()] = alim.find('alim_nom_eng').text.strip()

ciqual_ingredients = {}

# Compo file is not valid XML. Need to fix all of the "less than" entries
with open(os.path.join(os.path.dirname(__file__), "assets/ciqual/compo_2020_07_07.xml"), encoding="utf8") as compo_file:
    compo_table = ET.fromstring(compo_file.read().replace(' < ', ' &lt; '))

# Code below creates the ciqual_stats.csv file
# Note need to uncomment other lines below too
# ciqual_csv_file = open(os.path.join(os.path.dirname(__file__), 'assets/ciqual/ciqual_stats.csv'), "w", newline="")
# ciqual_csv = csv.writer(ciqual_csv_file)
# ciqual_csv.writerow(['alim_code', 'alim_nom_eng', 'nutrient', 'min', 'nom', 'max', 'confidence', 'minus', 'plus'])

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
        nom_value = parse_value(teneur) / factor

        has_min = True
        if min is not None:
            min_value = parse_value(min.strip()) / factor
        elif '<' in teneur:
            min_value = 0
        else:
            min_value = nom_value
            has_min = False

        has_max = True
        if max is not None:
            max_value = parse_value(max.strip()) / factor
        else:
            max_value = nom_value
            has_max = False

        alim_nom_eng = alim_codes[alim_code]
        confidence = compo.find('code_confiance').text
        # Looking at the data the code confidence doesn't seem to affect the min / max range
        #
        # Confidence | Average Minus | Average Plus
        #     A      |      42%      |     704%
        #     B      |      25%      |      36%
        #     C      |      31%      |      45%
        #     D      |      36%      |      62%
        #
        # Hence we can't really use it to set a percentage range
        #
        # Code below creates the ciqual_stats.csv file
        # ciqual_csv.writerow([alim_code, alim_nom_eng, nutrient_key, min_value, nom_value, max_value,
        #                      confidence.strip() if confidence is not None else '',
        #                      round(100 * (nom_value - min_value) / nom_value, 2) if has_min and nom_value > 0 else '',
        #                      round(100 * (max_value - nom_value) / nom_value, 2) if has_max and nom_value > 0 else ''])

        ciqual_ingredient = ciqual_ingredients.setdefault(alim_code, {
            'id': alim_code,
            'ciqual_food_code': alim_code,
            'alim_nom_eng': alim_nom_eng,
            'text': alim_nom_eng,
            'nutrients': {},
        })
        ciqual_ingredient = ciqual_ingredients.get(alim_code, {})
        ciqual_ingredient['nutrients'][nutrient_key] = {
            'percent_nom': nom_value,
            'percent_min': min_value,
            'percent_max': max_value,
            'confidence' : confidence.strip() if confidence is not None else 'D'
        }

# Code below creates the ciqual_stats.csv file
# ciqual_csv_file.close()

# Load ingredients
filename = os.path.join(os.path.dirname(__file__), "assets/taxonomies/ingredients.json")
with open(filename, "r", encoding="utf-8") as ingredients_file:
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
                    print('Obtained ciqual_code from ' + parent_id)
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
                        ingredient_nutrients[off_id] = {'percent_min': 0, 'percent_nom': 0, 'percent_max': 100}
                else:
                    ingredient['alim_nom_eng'] = ciqual_ingredient['alim_nom_eng']
                    ingredient_nutrients = ciqual_ingredient['nutrients']

                ingredient['nutrients'] = ingredient_nutrients
                ingredient['ciqual_food_code_used'] = ciqual_code


def prepare_product(product):
    setup_ingredients(product['ingredients'], product.get('nutriments', {}))

# Product Opener sometimes store numbers as strings when it outputs JSON
def ensure_float(value):
    if isinstance(value, str):
        value = value.replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return 0.0
    return float(value)

# Dump ingredients
#with open(filename, "w", encoding="utf-8") as ingredients_file:
#    json.dump(
#        ingredients, ingredients_file, sort_keys=True, indent=4, ensure_ascii=False
#    )
