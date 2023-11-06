import requests

from ciqual.nutrients import prepare_product


def print_recipe(ingredients, indent = ''):
    for ingredient in ingredients:
        lost_water = ingredient.get('evaporation', '')
        if type(lost_water) == float:
            lost_water = '(' + str(lost_water) + ')'
        print(indent, '-', ingredient['text'], ingredient['proportion'], lost_water)
        if 'ingredients' in ingredient:
            print_recipe(ingredient['ingredients'], indent + ' ')


# TODO: Tests
def assign_weightings(product):
    # Determine which nutrients will be used in the analysis by assigning a weighting
    product_nutrients = product['nutriments']
    count = product['recipe_estimator']['ingredient_count']
    computed_nutrients = product['recipe_estimator']['nutrients']

    for nutrient_key in computed_nutrients:
        computed_nutrient = computed_nutrients[nutrient_key]
        product_nutrient = product_nutrients.get(nutrient_key)
        if product_nutrient is None:
            computed_nutrient['notes'] = 'Not listed on product'
            continue

        computed_nutrient['product_total'] = product_nutrient
        if nutrient_key == 'energy':
            computed_nutrient['notes'] = 'Energy not used for calculation'
            continue

        if product_nutrient == 0 and computed_nutrient['unweighted_total'] == 0:
            computed_nutrient['notes'] = 'All zero values'
            continue

        if computed_nutrient['ingredient_count'] != count:
            computed_nutrient['notes'] = 'Not available for all ingredients'
            continue

        # Weighting based on size of ingredient, i.e. percentage based
        # Comment out this code to use weighting specified in nutrient_map.csv
        if product_nutrient > 0:
            computed_nutrient['weighting'] = 1 / product_nutrient
        else:
            computed_nutrient['weighting'] = min(0.01, count / computed_nutrient['unweighted_total']) # Weighting below 0.01 causes bad performance, although it isn't that simple as just multiplying all weights doesn't help

        # Favor Sodium over salt if both are present
        #if not 'error' in nutrients.get('Sodium (mg/100g)',{}) and not 'error' in nutrients.get('Salt (g/100g)', {}):
        #    nutrients['Salt (g/100g)']['error'] = 'Prefer sodium where both present'


def get_product(id):
    response = requests.get("https://world.openfoodfacts.org/api/v3/product/" + id).json()
    if not 'product' in response:
        return {}

    product = response['product']
    prepare_product(product)
    assign_weightings(product)

    return product

