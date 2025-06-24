# Install dependencies

## Frontend

This is a create-react-app project.

To set up:

```
cd ./frontend
npm install
npm run build
```

This creates the static folder in the backend so that static files can be served by FastAPI. (Path is set in the .env file)

## Backend

This is using Python3.

Create a virtualenv.
```
python -m venv venv 
```

Enter virtualenv (Windows).
```
venv/Scripts/activate
```
or (Linux)
```
source venv/bin/activate
```

Install requirements.
```
pip install -r requirements.txt
```

# Running Locally

To run the API server:

```
uvicorn recipe_estimator.main:app --reload
```

The static pages can be accessed like this:

To test:
http://localhost:8000/static/#product_code

e.g.

http://localhost:8000/static/#0677294998025

To run the frontend with dynamic reloading (in a new terminal):
```
cd ./frontend
npm start
```

To test:
http://localhost:3000/#product_code

e.g.

http://localhost:3000/#0677294998025

# Running Unit Tests

The server unit tests can be run with `pytest` at the command line or using the Testing panel in the Python VSCode plugin.

There are currently no frontend unit tests.

# Building the Docker Image

From the project root folder:
```
docker build --tag recipe_estimator .  
```
And to run:
```
docker run --name recipe_estimator -dp 5520:80 recipe_estimator
```

# Processing Steps

## Obtain Nutrients for Ingredients

For each ingredient we need to obtain the expected nutrient breakdown. This currently comes from the CIQUAL database, but other databases could be used, e.g. based on a regional preference.

If the ingredient on the product doesn't currently have a CIQUAL code then attempt to look this up is made using ingredients.json. To refresh the ingredients taxonomy you can run:

```
make refresh_ingredients_taxonomy
```

Having found the ingredient in CIQUAL a nutrient map is added to each ingredient. Only the "main" nutrient is used (the one with a `_100g` suffix).

## Determine nutrients for computation

Only nutrients that occur on every ingredient can be used. Energy is also eliminated as this combines multiple nutrients.

## Weighting

A weighting can be applied to give specific nutrients more / less impact on the overall calculation. If a nutrient has no weighting then 1 is assumed.

## Estimation

The estimation attempts to find the proportion of each ingredient that minimises the weighted difference between the computed nurtients and those obtained from the product.

## Return data

An example return structure is shown below:

```json
ingredients: [
  {
    id: "en:tomato",
    percent_estimate: 67.2,
    evaporation: 4,
    nutrients: {
      calcium: {percent_min: 0.023, percent_max: 0.024},
      carbohydrates: {percent_min: 3.45, percent_max: 3.45},
      ...
    }
  },
  ...
],
recipe_estimator: {
  nutrients: {
    calcium: {
      product_total: 0.06,
      weighting: 1000,
    },
    vitamin-b2: {
      notes: "Not listed on product"
    },
    ...
  },
  ingredient_count: 3,
  iterations: 35,
  status: 0,
  time: 0.2
}
```

### Ingredients

The original ingredients map will be returned with additional percent_estimate field and a nutrients map with the expected nutrient value ranges in g per 100 g/ml of that ingredient.

A quantity_estimate field is also provided which shows the amount of the ingredient needed to make 100 g/ml of the product. Note this may be higher than the percent_estimate because of evaporation during the product preparation / processing. An evaporation field shows the estimated water loss during processing.

### Recipe Estimator

A new "recipe_estimator" map will also be returned, providing the compted nutrients and some metrics

#### Nutrients

This will contain the calculated value based on the new estimate and will also provide the weighting used, the nutrient identifier for the database used (CIQUAL), the quoted proportion from the product and the difference from the computed value. Nutrients that were not quoted on the product will also be included.

#### Metrics

This will provide details of the computation performed, such as time taken and number of iterations.


# TODO

 - Need to return a more formal error object
 - Use min and max for ingredient nutrient when stated as "< ..." in CIQUAL
 - Use min and max from CIQUAL for unmatched ingredients
 - Cope with min and max on product nutrients (e.g. if we had to get from a category)


# Background Info

To get nutrient types for nutrient_map.csv I used:

```js
db.products.aggregate([
  {
    $project: {
      keys: {
        $map: {
          input: {
            "$objectToArray": "$nutriments"
          },
          in: "$$this.k"
        }
      }
    }
  },
  {
    $unwind: "$keys"
  },
  {
    $group: {
      _id: "$keys",
      count: {
        "$sum": 1
      }
    }
  }
])
```

Need to skip any nutrients where Ciqual value is '-' as this means not known, not zero