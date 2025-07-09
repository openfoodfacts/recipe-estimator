import json
import os
import xml.etree.ElementTree as ET
from recipe_estimator.nutrient_map import ciqual_to_off

def parse_value(ciqual_nutrient):
    if not ciqual_nutrient or ciqual_nutrient == '-':
        return 0
    return float(ciqual_nutrient.replace(',','.').replace('<','').replace('traces','0'))

const_codes = {}
const_table = ET.parse(os.path.join(os.path.dirname(__file__), "../ciqual/const_2020_07_07.xml")).getroot()
for const in const_table:
    const_codes[const.find('const_code').text.strip()] = const.find('const_nom_eng').text.strip()

# Load Ciqual data
alim_codes = {}
alim_table = ET.parse(os.path.join(os.path.dirname(__file__), "../ciqual/alim_2020_07_07.xml")).getroot()
for alim in alim_table:
    alim_codes[alim.find('alim_code').text.strip()] = alim.find('alim_nom_eng').text.strip()

ciqual_ingredients = {}

# Compo file is not valid XML. Need to fix all of the "less than" entries
with open(os.path.join(os.path.dirname(__file__), "../ciqual/compo_2020_07_07.xml"), encoding="utf8") as compo_file:
    compo_table = ET.fromstring(compo_file.read().replace(' < ', ' &lt; '))

# Code below creates the ciqual_stats.csv file
# TODO: Need to not do this here anymore as it won't take sugars into account
# Note need to uncomment other lines below too
# ciqual_csv_file = open(os.path.join(os.path.dirname(__file__), 'assets/ciqual/ciqual_stats.csv'), "w", newline="")
# ciqual_csv = csv.writer(ciqual_csv_file)
# ciqual_csv.writerow(['alim_code', 'alim_nom_eng', 'nutrient', 'min', 'nom', 'max', 'confidence', 'minus', 'plus'])

# Populate the nutrients for each ingredient
for compo in compo_table:
    const_code = compo.find('const_code').text.strip()
    nutrient = ciqual_to_off.get(const_codes.get(const_code))
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
            'confidence' : confidence.strip() if confidence is not None and teneur != '-' else '-'
        }

# Post-process sugars as some items, like fructose, don't quote sugars but so quote the individual parts
for ciqual_ingredient in ciqual_ingredients.values():
    nutrients = ciqual_ingredient['nutrients']
    sugars = nutrients.get('sugars')
    if sugars and sugars.get('confidence') == '-':
        # Loop through the other sugars and add them up
        min = 0
        max = 0
        nom = 0
        con = 0
        for nutrient in ['fructose', 'galactose', 'lactose', 'maltose', 'sucrose']:
            sugar = nutrients.get(nutrient)
            if sugar:
                min += sugar.get('percent_min', 0)
                max += sugar.get('percent_max', 0)
                nom += sugar.get('percent_nom', 0)
                # For some reason max throws an exception here
                newcon = '-ABCD'.index(sugar.get('confidence', '-'))
                if newcon > con:
                    con = newcon

        sugars['percent_min'] = min
        sugars['percent_max'] = max
        sugars['percent_nom'] = nom
        sugars['confidence'] = '-ABCD'[con]

# Code below creates the ciqual_stats.csv file
# ciqual_csv_file.close()

filename = os.path.join(os.path.dirname(__file__), "../recipe_estimator/assets/ciqual_ingredients.json")
with open(filename, 'w', encoding='utf-8') as f:
  f.write(json.dumps(ciqual_ingredients, ensure_ascii=False, sort_keys=True, indent=2))
