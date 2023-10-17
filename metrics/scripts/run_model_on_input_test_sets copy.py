#!/usr/bin/python3
"""
run_model_input_test_sets.py [path to model executable] [path to store results] [paths of one or more input test sets]

The model executable must:
- accept a product JSON body as input in STDIN
- estimate ingredients percentages and store the result in the "percent_estimate" field of ingredients in the "ingredients" structure
- write the resulting product JSON to STDOUT

This script will go through each product JSON file of the specified input test sets to:
- Remove any specified "percent" fields from the ingredients
- Run the specified model on the product
- Save the resulting products in [path to store results]/[input test set name]/
"""

import json
import sys
import os

# Check input parameters (existing model executable, and specified results path + at least 1 input test set), otherwise print usage
if len(sys.argv) < 3:
    print("Usage: run_model_input_test_sets.py [path to model executable] [path to store results] [paths of one or more input test sets]")
    sys.exit(1)

model = sys.argv[1]
results_path = sys.argv[2]

if not os.path.exists(model):
    print("Model executable does not exist")
    sys.exit(1)

# Go through each input test set directory
for test_set_path in sys.argv[3:]:

    # Test set name is the last component of the test set path
    test_set_name = test_set_path.split("/")[-1]

    # Create the results directory if it does not exist
    if not os.path.exists(results_path):
        os.makedirs(results_path)
    # Create the results directory for the test set if it does not exist
    if not os.path.exists(results_path + "/" + test_set_name):
        os.makedirs(results_path + "/" + test_set_name)

    # Go through each JSON file in the input test set directory
    for path in [test_set_path + "/" + f for f in os.listdir(test_set_path) if f.endswith(".json")]:

        # test name is the last component of the path
        test_name = path.split("/")[-1]

        # Call the model executable with the product as input to STDIN and save the result from STDOUT
        result = os.popen(model + " < " + path).read()

        # Pretty save the resulting JSON structure over the input file for easy inspection of diffs
        result_path = results_path + "/" + test_set_name + "/" + test_name
        with open(result_path, "w") as f:
            print("Saving result: " + result_path)
            json.dump(result, f, indent=4)
