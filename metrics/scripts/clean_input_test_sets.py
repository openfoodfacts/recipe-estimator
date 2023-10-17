#!/usr/bin/python3
"""
clean_input_test_sets.py [paths of one or more input test sets]

This script will go through each product JSON file of the specified input test sets to:
- Remove the API v3 wrapping structure around the product data, if present
- Remove fields that are not relevant to the recipe calculation
- Pretty print the resulting JSON structure for easy inspection of diffs
"""

import json
import sys
import os

# Print usage
if len(sys.argv) < 2:
    print("Usage: clean_input_test_sets.py [paths of one or more input test sets]")
    sys.exit(1)

# Whitelist approach to keep only fields that may be relevant to recipe calculations
# If we need to add a field later on, we can always fetch it back with its barcode
# use * as wildcard
def filter_fields(data):
    # Note: we keep the ingredients structure as-is if it exists
    # if it doesn't exit, we will also need to run analyze_ingredients_for_input_test_sets
    whitelist = ['ingredients', 'ingredients_text', 'ingredients_lc', 'lc', 'nutriments', 'categories_tags', 'labels_tags', 'countries_tags']
    return {k: v for k, v in data.items() if k in whitelist}

# Go through each input test set directory
for test_set_path in sys.argv[1:]:

    # Go through each JSON file in the input test set directory
    for path in [test_set_path + "/" + f for f in os.listdir(test_set_path) if f.endswith(".json")]:

        with open(path, "r") as f:
            data = json.load(f)

        # Remove the API v3 wrapping structure around the product data, if present
        if "product" in data:
            data = data["product"]

        # Remove fields that are not relevant to the recipe calculation
        data = filter_fields(data)

        # Pretty save the resulting JSON structure over the input file for easy inspection of diffs
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
