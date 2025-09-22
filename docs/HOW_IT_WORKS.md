# How Recipe Estimation Works

## Overview

The Recipe Estimator analyzes food products to estimate the proportions of their ingredients based on nutritional information. It uses optimization techniques to find ingredient proportions that best match the product's declared nutritional values.

## Processing Steps

### 1. Obtain Nutrients for Ingredients

For each ingredient, we need to obtain the expected nutrient breakdown. This currently comes from the CIQUAL database, but other databases could be used (e.g., based on regional preferences).

If an ingredient doesn't have a CIQUAL code, the system attempts to look it up using `ingredients.json`. 

Having found the ingredient in CIQUAL, a nutrient map is added to each ingredient using only the "main" nutrient (with `_100g` suffix).

### 2. Determine Nutrients for Computation

Only nutrients that occur on every ingredient can be used in the computation. Energy is eliminated as it combines multiple nutrients.

### 3. Weighting

A weighting system can be applied to give specific nutrients more or less impact on the overall calculation. If a nutrient has no weighting, a value of 1 is assumed.

### 4. Estimation

The estimation algorithm attempts to find the proportion of each ingredient that minimizes the weighted difference between:
- Computed nutrients (based on ingredient proportions)  
- Declared nutrients from the product

The system supports two optimization algorithms:
- **GLOP**: Linear programming solver
- **SciPy**: Non-linear optimization

### 5. Return Data

The API returns detailed results including:

#### Ingredients
- Original ingredients with additional `percent_estimate` field
- `quantity_estimate`: Amount needed to make 100g/ml of product  
- `evaporation`: Estimated water loss during processing
- `nutrients`: Expected nutrient value ranges per ingredient

#### Recipe Estimator Metrics
- `nutrients`: Calculated values with weightings and differences
- `ingredient_count`: Number of ingredients processed
- `iterations`: Algorithm iterations performed  
- `status`: Computation status code
- `time`: Processing time in seconds

## Example Output Structure

```json
{
  "ingredients": [
    {
      "id": "en:tomato",
      "percent_estimate": 67.2,
      "evaporation": 4,
      "nutrients": {
        "calcium": {"percent_min": 0.023, "percent_max": 0.024},
        "carbohydrates": {"percent_min": 3.45, "percent_max": 3.45}
      }
    }
  ],
  "recipe_estimator": {
    "nutrients": {
      "calcium": {
        "product_total": 0.06,
        "weighting": 1000
      },
      "vitamin-b2": {
        "notes": "Not listed on product"
      }
    },
    "ingredient_count": 3,
    "iterations": 35,
    "status": 0,
    "time": 0.2
  }
}
```

## Technical Notes

- The `percent_estimate` may be lower than `quantity_estimate` due to evaporation during processing
- Nutrients not declared on the product are still estimated and included
- The system handles confidence levels from the CIQUAL database but doesn't use them for percentage ranges due to high variance