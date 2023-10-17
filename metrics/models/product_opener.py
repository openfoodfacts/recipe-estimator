#!/usr/bin/python3
"""
product_opener.py < input JSON product > output JSON product

Wrapper around the Product Opener API to estimate the ingredients percent of a product
"""

import requests
import json
import sys

# Check that we have an input product in JSON format in STDIN
try:
    product = json.load(sys.stdin)
    print("Input product is in JSON format")
except ValueError:
    print("Input product is not in JSON format")

# Call API v3 ingredients_analysis service
product_opener_api_url = "http://world.openfoodfacts.localhost/api/v3/product_services"
request_data = {
    "services": ["estimate_ingredients_percent"],
    "fields": ["all"],
    "product": product
}
response = requests.post(product_opener_api_url, json=request_data)

response_json = response.json()

if response_json["status"] != "success":
    print(response_json)
elif "product" in response_json:
    # Pretty print the resulting JSON structure over the input file for easy inspection of diffs
    print(json.dumps(response_json["product"], indent=4))
