import gzip
import json


# go through the ingredients recursively and sum the percent_estimate field of each ingredient
# input: ingredients - recursive ingredients structure
# output: ingredients_percent_estimates - dict of summed percent_estimate fields for each ingredient id
def sum_ingredients_estimates_for_product(ingredients, ingredients_percent_estimates):
    for ingredient in ingredients:
        if ('ingredients' in ingredient):
            # Child ingredients
            sum_ingredients_estimates_for_product(ingredient['ingredients'], ingredients_percent_estimates)
        
        ingredient_id = ingredient['id']
        percent_estimate = ingredient['percent_estimate']
        if (percent_estimate is not None):
            if ingredient_id in ingredients_percent_estimates:
                ingredients_percent_estimates[ingredient_id] += percent_estimate
            else:
                ingredients_percent_estimates[ingredient_id] = percent_estimate

def read_openfoodfacts_products(file_path, ingredients_values, num_products=None):
    products_ingredients = []
    
    with gzip.open(file_path, 'rt', encoding='utf-8') as file:
        for line in file:
            product = json.loads(line.strip())
            # if we have ingredients, sum the percent_estimate fields
            if 'ingredients' in product:
                ingredients_percent_estimates = {}
                sum_ingredients_estimates_for_product(product['ingredients'], ingredients_percent_estimates)

                # append the ingredient values to the ingredients_values dict
                for ingredient_id in ingredients_percent_estimates:
                    append_ingredient_value(ingredients_values, ingredient_id, ingredients_percent_estimates[ingredient_id])
                product_ingredients = ingredients_percent_estimates
                products_ingredients.append(product_ingredients)
            if num_products is not None and len(products_ingredients) >= num_products:
                break
    return products_ingredients

def append_ingredient_value(ingredients_values, ingredient_id, value):
    if ingredient_id in ingredients_values:
        ingredients_values[ingredient_id].append(value)
    else:
        ingredients_values[ingredient_id] = [value]

def compute_stats(ingredients_values):
    stats = {}
    for ingredient_id in ingredients_values:
        values = ingredients_values[ingredient_id]
        stats[ingredient_id] = {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / len(values),
            'stddev': (sum((x - sum(values) / len(values)) ** 2 for x in values) / len(values)) ** 0.5
        }
    return stats

file_path = '../data/openfoodfacts-products.jsonl.gz'
ingredients_values = {}
products_ingredients = read_openfoodfacts_products(file_path, ingredients_values, 10000)
print(f"Loaded {len(products_ingredients)} products")

# Print output for all products

for product_ingredients in products_ingredients:
    print(product_ingredients)

# Compute and print stats for all ingredients
stats = compute_stats(ingredients_values)

# print stats, by increasing order of count
for ingredient_id in sorted(stats, key=lambda x: stats[x]['count']):
    print(ingredient_id, stats[ingredient_id])