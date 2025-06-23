from ciqual.nutrients import off_to_ciqual


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
                    proportion = ingredient_nutrients[off_id]['percent_nom']
                    existing_nutrient = nutrients.get(off_id)
                    if (existing_nutrient is None):
                         nutrients[off_id] = {'ingredient_count': 1, 'unweighted_total': proportion, 'weighting': 0}
                    else:
                        existing_nutrient['ingredient_count'] = existing_nutrient['ingredient_count'] + 1
                        existing_nutrient['unweighted_total'] = existing_nutrient['unweighted_total'] + proportion

    return count

def assign_weightings(product):
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

        if computed_nutrient['ingredient_count'] != count:
            computed_nutrient['notes'] = 'Not available for all ingredients'
            continue

        nutrient = off_to_ciqual[nutrient_key]
        weighting = nutrient['weighting']
        if weighting == '':
            computed_nutrient['notes'] = nutrient['comments']
        else:
            computed_nutrient['weighting'] = float(weighting)

        penalty_factor = nutrient['penalty_factor']
        computed_nutrient['penalty_factor'] = 0 if penalty_factor == '' else float(penalty_factor)
        
    # Exclude carbohydrates if one of these is true
    # 1. We have a value for both sugars and fibre
    # 2. The countries_tags includes "en:united-states" (carbs could be gross rather than net)
    carbohydrates = computed_nutrients.get('carbohydrates')
    if (carbohydrates and carbohydrates['weighting'] > 0):
        if 'countries_tags' not in product or 'en:united-states' in product['countries_tags']:
            carbohydrates['weighting'] = 0
            carbohydrates['notes'] = 'Possible US product quoting gross carbs'
        else:
            fiber = computed_nutrients.get('fiber')
            sugars = computed_nutrients.get('sugars')
            if fiber and sugars and fiber['weighting'] > 0 and sugars['weighting'] > 0:
                carbohydrates['weighting'] = 0
                carbohydrates['notes'] = 'Have sugar and fiber so ignore carbs'


def prepare_nutrients(product):
    nutrients = {}
    count = count_ingredients(product['ingredients'], nutrients)
    product['recipe_estimator'] = {'nutrients':nutrients, 'ingredient_count': count}
    assign_weightings(product)
    return count