# These are the rules from the Wiki:
# 1. No ingredient maximum can be bigger than 100% - sum of all known percentages
# 2. The maximum value for an ingredient coming after a known ingredient can be no bigger than the preceding known ingredient percentage.
#    Immediately following unknown ingredient maximum values can be no bigger than this value divided by their distance from the preceding known ingredient.
#    e.g. if ingredient 2 is 20% then ingredient 3 has a maximum value of 20% and ingredient 4 has a maximum value of 10%.
#    Note this is a more general definition of the rule for top level ingredients where the maximum value is 100% divided by the ingredient position.
# 3. An ingredient maximum value can be no bigger than 100% minus the sum of all previous ingredient minimum percentages
# 4. No ingredient minimum percentage can be smaller than the first following ingredient that has a known percentage
# 5. The first unknown ingredient can have a minimum value that is no less than than (100% - the sum of preceding known ingredients) / the number of remaining ingredients.
#    This is a more general case of the rule for a first top level ingredient having a minimum of 100% / number of ingredients.
#    For compound ingredients use the minimum value of the parent ingredient instead of 100% in this formula.
# 6. The minimum percentage for a compound ingredient can be no less than the sum of all child ingredient minimum percentages

def sum_of_known_ingredients(ingredients):
    total_percent = 0
    for ingredient in ingredients:
        percent = ingredient.get("percent")
        if percent is not None:
            total_percent += percent
        elif "ingredients" in ingredient:
            total_percent += sum_of_known_ingredients(ingredient["ingredients"])

def calculate_min_max(ingredients):
    known_percentages = sum_of_known_ingredients(ingredients)
    
def assign_bounds(ingredients, parent_min=100, parent_max=100, stop_before=-1):
    num_ingredients = len(ingredients)
    before_max = parent_max
    last_percent_index = -1
    for n,ingredient in enumerate(ingredients):
        if stop_before > -1 and n >= stop_before:
            break
        percent = ingredient.get("percent")
        if percent is not None:
            before_max -= percent
            # Go back to the start and make sure the maxima are limited based on the new information
            assign_bounds(ingredients, parent_min, before_max, n)
            parent_max = percent
            parent_min = percent
            last_percent_index = n
            min = percent
            max = percent
        else:
            min = round(0 if n > (last_percent_index + 1) else parent_min / (num_ingredients - (last_percent_index + 1)), 2)
            max = round(parent_max / (n + 1 - (last_percent_index + 1)), 2)

        ingredient['percent_min'] = min
        ingredient['percent_max'] = max
        if "ingredients" in ingredient:
            assign_bounds(ingredient["ingredients"], min, max)
        
    return