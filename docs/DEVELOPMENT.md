# Development Guide

## Running the Application Locally

### Backend (API Server)

To run the API server with auto-reload:

```bash
uvicorn recipe_estimator.main:app --reload
```

Or using the Makefile:
```bash
make watch
```

The API will be available at `http://localhost:8000` (or `http://localhost:5521` when using the Makefile).

### Frontend (Development Mode)

To run the frontend with dynamic reloading:

```bash
cd ./frontend
npm start
```

Or using the Makefile:
```bash
make watch_frontend
```

The frontend will be available at `http://localhost:3000`.

### Testing the Application

#### Static Pages via Backend
- Test URL: `http://localhost:8000/static/#product_code`
- Example: `http://localhost:8000/static/#0677294998025`

#### Frontend Development Server  
- Test URL: `http://localhost:3000/#product_code`  
- Example: `http://localhost:3000/#0677294998025`

#### Docker Compose
If using docker-compose, the application will be available at:
- Example: `http://localhost:5520/static/#0677294998025`

## Running Tests

### Backend Tests
Run the server unit tests with pytest:
```bash
pytest
```

Or with arguments:
```bash
make tests args="--verbose"
```

### Frontend Tests  
Currently, there are no frontend unit tests.

## Docker Development

### Building the Image
```bash
docker build --tag recipe_estimator .
```

Or using docker-compose:
```bash
make build
```

### Running with Docker
```bash
docker run --name recipe_estimator -dp 5520:5521 recipe_estimator
```

Or using docker-compose:
```bash
make up
```

This will build and run the application with dependencies.