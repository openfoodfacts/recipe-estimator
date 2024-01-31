
# count the number of leaf ingredients in the product
# for each nutrient, store in nutrients the number of leaf ingredients that have a nutrient value
# and the sum of the percent_max of the corresponding ingredients
def count_ingredients(ingredients, nutrients):
    count = 0
    for ingredient in ingredients:
        if ('ingredients' in ingredient):
            # Child ingredients
            child_count = count_ingredients(ingredient['ingredients'], nutrients)
            if child_count == 0:
                return 0
            count = count + child_count

        else:
            count = count + 1
            ingredient_nutrients = ingredient.get('nutrients')
            if (ingredient_nutrients is not None):
                for off_id in ingredient_nutrients:
                    proportion = ingredient_nutrients[off_id]['percent_max'] # Use the maximum in a range for weighting
                    existing_nutrient = nutrients.get(off_id)
                    if (existing_nutrient is None):
                         nutrients[off_id] = {'ingredient_count': 1, 'unweighted_total': proportion}
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

        # Energy is derived from other nutrients, so don't use it
        if nutrient_key == 'energy':
            computed_nutrient['notes'] = 'Energy not used for calculation'
            continue

        # Sodium is computed from salt, so don't use it, to avoid double counting
        if nutrient_key == 'sodium':
            computed_nutrient['notes'] = 'Sodium not used for calculation'
            continue

        if product_nutrient == 0 and computed_nutrient['unweighted_total'] == 0:
            computed_nutrient['notes'] = 'All zero values'
            continue

        if computed_nutrient['ingredient_count'] != count:
            computed_nutrient['notes'] = 'Not available for all ingredients'
            continue

        # Favor Sodium over salt if both are present
        #if not 'error' in nutrients.get('Sodium (mg/100g)',{}) and not 'error' in nutrients.get('Salt (g/100g)', {}):
        #    nutrients['Salt (g/100g)']['error'] = 'Prefer sodium where both present'

        # Weighting based on size of ingredient, i.e. percentage based
        # Comment out this code to use weighting specified in nutrient_map.csv
        try:
            if product_nutrient > 0:
                computed_nutrient['weighting'] = 1 / product_nutrient
            else:
                computed_nutrient['weighting'] = min(0.01, count / computed_nutrient['unweighted_total']) # Weighting below 0.01 causes bad performance, although it isn't that simple as just multiplying all weights doesn't help
        except Exception as e:
            computed_nutrient['notes'] = e

        if nutrient_key == 'salt':
            computed_nutrient['weighting'] = 100
            continue
         

        computed_nutrient['weighting'] = 1


def prepare_nutrients(product):
    nutrients = {}
    count = count_ingredients(product['ingredients'], nutrients)
    product['recipe_estimator'] = {'nutrients':nutrients, 'ingredient_count': count}
    assign_weightings(product)
    return