import os
import urllib.request
import json

with open(os.path.join(os.path.dirname(__file__), "../recipe_estimator/assets/ciqual_ingredients.json"), "r", encoding="utf-8") as ciqual_file:
    ciqual = json.load(ciqual_file)

with open(os.path.join(os.path.dirname(__file__), "../recipe_estimator/assets/ingredients.json"), "r", encoding="utf-8") as ingredients_file:
    ingredients = json.load(ingredients_file)

with urllib.request.urlopen("https://static.openfoodfacts.org/data/taxonomies/categories.json") as url:
    categories = json.load(url)

def check_taxonomy(taxonomy):
    missing_codes = []
    name_differences = []
    missing_proxy_codes = []
    for id, item in taxonomy.items():
        if 'ciqual_food_code' in item:
            item_name = item.get("name", {}).get("en")
            ciqual_code = item['ciqual_food_code'].get('en')
            ciqual_name_en = item.get('ciqual_food_name', {}).get('en')
            ciqual_ingredient = ciqual.get(ciqual_code)
            if not ciqual_ingredient:
                missing_codes.append(f"{id} ({item_name}): Can't find CIQUAL code {ciqual_code} ({ciqual_name_en})")
            else:
                alim_nom_eng = ciqual_ingredient.get("alim_nom_eng")
                if ciqual_name_en != alim_nom_eng:
                    name_differences.append(f"{id} ({item_name}): Names don't match for CIQUAL code {ciqual_code} ({ciqual_name_en} / {alim_nom_eng})")

        if 'ciqual_proxy_food_code' in item:
            item_name = item.get("name", {}).get("en")
            ciqual_code = item['ciqual_proxy_food_code'].get('en')
            ciqual_name_en = item.get('ciqual_proxy_food_name', {}).get('en')
            ciqual_ingredient = ciqual.get(ciqual_code)
            if not ciqual_ingredient:
                missing_proxy_codes.append(f"{id} ({item_name}): Can't find proxy CIQUAL code {ciqual_code} ({ciqual_name_en})")
    return missing_codes, missing_proxy_codes, name_differences

ingredient_missing_codes, ingredient_missing_proxy_codes, ingredient_name_differences = check_taxonomy(ingredients)
category_missing_codes, category_missing_proxy_codes, category_name_differences = check_taxonomy(categories)

print("--- Ingredients Missing Codes ---")
print("\n".join(ingredient_missing_codes))
print("--- Ingredients Missing Proxy Codes ---")
print("\n".join(ingredient_missing_proxy_codes))
print("--- Ingredients Name Differences ---")
print("\n".join(ingredient_name_differences))
print("")
print("--- Categories Missing Codes ---")
print("\n".join(category_missing_codes))
print("--- Categories Missing Proxy Codes ---")
print("\n".join(category_missing_proxy_codes))
print("--- Categories Name Differences ---")
print("\n".join(category_name_differences))
print("")
print("*** Ingredients Summary ***")
print(f"{len(ingredient_missing_codes)} missing codes")
print(f"{len(ingredient_missing_proxy_codes)} missing proxy codes")
print(f"{len(ingredient_name_differences)} name differences")
print("*** Categories Summary ***")
print(f"{len(category_missing_codes)} missing codes")
print(f"{len(category_missing_proxy_codes)} missing proxy codes")
print(f"{len(category_name_differences)} name differences")
