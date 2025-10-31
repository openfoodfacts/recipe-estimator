import os
import urllib.request, json 
with urllib.request.urlopen("https://static.openfoodfacts.org/data/taxonomies/ingredients.json") as url:
    data = json.load(url)
    filename = os.path.join(os.path.dirname(__file__), "../recipe_estimator/assets/ingredients.json")
    with open(filename, 'w', encoding='utf-8') as f:
      f.write(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2))
