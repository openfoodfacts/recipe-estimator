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
cd ./backend
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
cd ./backend
uvicorn main:app --reload
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

# Building the Docker Image

From the project root folder:
```
docker build --tag recipe-estimator .  
```
And to run:
```
docker run -dp 8000:80 recipe-estimator
```

# Processing Steps

## Obtain Nutrients for Ingredients

For each ingredient we need to obtain the expected nutrient breakdown. This currently comes from the CIQUAL database, but other databases could be used, e.g. based on a regional preference.

This process adds a nutrient map to each ingredient. Only the "main" nutrient is used (one without an underscore suffix).

A separate map is also returned providing the CIQUAL database identifier for each OFF nutrient.

## Determine nutrients for computation

Only nutrients that occur on every ingredient can be used. Energy is also eliminated as this combines multiple nutrients.

## Weighting

A weighting can be applied to give specific nutrients more / less impact on the overall calculation. If a nutrient has no weighting then 1 is assumed.

## Estimation

The estimation attempts to find the proportion of each ingredient that minimises the weighted difference between the computed nurtients and those obtained from the product.

## Return data

An example return structure is shown below:

```
ingredients: [
  {
    id: "en:tomato",
    percent_estimate2: 67.2,
    nutrients: {
      calcium: 0.024,
      carbohydrates: 3.45,
      ...
    }
  },
  ...
],
recipe_estimator: {
  nutrients: {
    calcium: {
      product_value: 0.06,
      estimated_value: 0.054,
      difference: -0.006,
      weighting: 1000,
      ciqual_id: "Calcium (mg/100g)"
    },
    vitamin-b2: {
      estimated_value: 0.0023,
      ciqual_id: "Vitamin B2 or Riboflavin (mg/100g)"
    },
    ...
  }
  metrics: {
    iterations: 35,
    time: 0.2,
    weighted_variance: 1.45
  }
}
```

### Ingredients

The original ingredients map will be returned with additional percent_estimate2 field and a nutrients map with the expected nutrient values in g per 100 g/ml of that ingredient.

### Recipe Estimator

A new "recipe_estimator" map will also be returned, providing the compted nutrients and some metrics

#### Nutrients

This will contain the calculated value based on the new estimate and will also provide the weighting used, the nutrient identifier for the database used (CIQUAL), the quoted proportion from the product and the difference from the computed value. Nutrients that were not quoted on the product will also be included.

#### Metrics

This will provide details of the computation performed, such as time taken and number of iterations.


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