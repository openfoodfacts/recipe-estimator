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

Enter virtualenv.
```
venv/Scripts/activate
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