from .nutrient_map import off_to_ciqual


# count the number of leaf ingredients in the product
# for each nutrient, store in nutrients the number of leaf ingredients that have a nutrient value
# and the sum of the percent_max of the corresponding ingredients
def count_ingredients(ingredients, nutrients):
    count = 0
    for ingredient in ingredients:
        if ('ingredients' in ingredient and len(ingredient['ingredients']) > 0):
            # Child ingredients
            child_count = count_ingredients(ingredient['ingredients'], nutrients)
            count = count + child_count

        else:
            count = count + 1
            ingredient_nutrients = ingredient.get('nutrients')
            if (ingredient_nutrients is not None):
                for off_id in ingredient_nutrients:
                    if ingredient_nutrients[off_id]['confidence'] != '-':
                        proportion = ingredient_nutrients[off_id]['percent_nom']
                        existing_nutrient = nutrients.get(off_id)
                        if (existing_nutrient is None):
                            nutrients[off_id] = {'ingredient_count': 1, 'unweighted_total': proportion, 'weighting': 0}
                        else:
                            existing_nutrient['ingredient_count'] = existing_nutrient['ingredient_count'] + 1
                            existing_nutrient['unweighted_total'] = existing_nutrient['unweighted_total'] + proportion

    return count

def assign_weightings(product, scipy):
    # Determine which nutrients will be used in the analysis by assigning a weighting
    product_nutrients = product.get('nutriments', {})
    count = product['recipe_estimator']['ingredient_count']
    computed_nutrients = product['recipe_estimator']['nutrients']

    for nutrient_key in computed_nutrients:
        computed_nutrient = computed_nutrients[nutrient_key]
        # Get nutrient value per 100g of product
        product_nutrient = product_nutrients.get(nutrient_key + '_100g', None)
        if product_nutrient is None:
            computed_nutrient['notes'] = 'Not listed on product'
            continue

        computed_nutrient['product_total'] = product_nutrient
        
        if product_nutrient == 0 and computed_nutrient['unweighted_total'] == 0:
            computed_nutrient['notes'] = 'All zero values'
            continue

        if computed_nutrient['ingredient_count'] == 0:
            computed_nutrient['notes'] = 'Not available on any ingredient'
            continue

        nutrient = off_to_ciqual[nutrient_key]
        weighting = nutrient['scipy_weighting'] if scipy else nutrient['weighting']
        if weighting == '':
            computed_nutrient['notes'] = nutrient['comments']
        else:
            computed_nutrient['weighting'] = float(weighting)
        
    # Exclude carbohydrates if the following make up more than 50% of the countries in the countries_tags:
    # United States, Canada, South Africa, Gulf States (carbs could be gross rather than net)
    carbohydrates = computed_nutrients.get('carbohydrates')
    if carbohydrates and carbohydrates['weighting'] > 0 and 'countries_tags' in product:
        gross_countries = len(set(['en:united-states', 'en:canada', 'en:south-africa','en:bahrain','en:kuwait', 'en:iraq', 'en:iran', 'en:oman', 'en:qatar', 'en:saudi-arabia', 'en:united-arab-emirates']) & set(product['countries_tags']))
        if gross_countries / len(product['countries_tags']) > 0.5:
            # If we subtract the sugar and fiber from the carbs and get a negative result then it can't be gross carbs
            fiber = computed_nutrients.get('fiber')
            sugars = computed_nutrients.get('sugars')
            remaining_carbs = carbohydrates['product_total']
            if fiber and sugars:
                remaining_carbs = remaining_carbs - fiber.get('product_total',0) - sugars.get('product_total',0)

            if remaining_carbs > 0:
                carbohydrates['weighting'] = 0
                carbohydrates['notes'] = 'Might be total carbs'


def prepare_nutrients(product, scipy = False):
    nutrients = {}
    count = count_ingredients(product['ingredients'], nutrients)
    product['recipe_estimator'] = {'nutrients':nutrients, 'ingredient_count': count}
    assign_weightings(product, scipy)
    return count