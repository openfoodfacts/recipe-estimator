#!/usr/bin/python3
"""
parse_ingredients_for_input_test_sets.py [paths of one or more input test sets]

This script calls the Product Opener API to parse the ingredients list and create the ingredients nested structure
for each product of each specified input test set.
"""

import json
import sys
import os
import requests

# Print usage
if len(sys.argv) < 2:
    print("Usage: parse_ingredients_for_input_test_sets.py [paths of one or more input test sets]")
    sys.exit(1)

# Go through each input test set directory
for test_set_path in sys.argv[1:]:

    # Go through each JSON file in the input test set directory
    for path in [test_set_path + "/" + f for f in os.listdir(test_set_path) if f.endswith(".json")]:

        with open(path, "r") as f:
            product = json.load(f)

        # Call API v3 ingredients_analysis service
        product_opener_api_url = "http://world.openfoodfacts.localhost/api/v3/product_services"
        request_data = {
            "services": ["parse_ingredients_text"],
            "fields": ["all"],
            "product": product
        }
        response = requests.post(product_opener_api_url, json=request_data)

        response_json = response.json()

        if response_json["status"] != "success":
            print(response_json)
            continue

        if "product" in response_json:

            # Pretty save the resulting JSON structure over the input file for easy inspection of diffs
            with open(path, "w") as f:
                print("Updating with ingredients structure: " + path)
                json.dump(response_json["product"], f, indent=4)
