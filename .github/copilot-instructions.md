# Recipe Estimator

Recipe Estimator is a Python FastAPI web application with a React TypeScript frontend that estimates ingredient proportions in food products based on nutrient information. It uses mathematical optimization algorithms to determine the most likely recipe composition.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Initial Setup
- Install Python dependencies: `pip install -r requirements.txt` -- takes 30 seconds initially, 2 seconds when cached.
- Install frontend dependencies: `cd ./frontend && npm install` -- takes 60 seconds initially, 5 seconds when cached. NEVER CANCEL. Set timeout to 90+ seconds.
- Build frontend: `cd ./frontend && npm run build` -- takes 20 seconds. NEVER CANCEL. Set timeout to 60+ seconds.
- Alternative: Use `make install` which runs both frontend build and pip install -- takes 15-60 seconds depending on cache.

### Running the Application
- Backend API server: `uvicorn recipe_estimator.main:app --port 5521 --reload` or `make watch`
- Frontend dev server: `cd ./frontend && npm start` or `make watch_frontend` -- runs on http://localhost:5522
- Access API documentation at http://localhost:5521/docs when backend is running
- Access static frontend at http://localhost:5521/static/ when backend is running (after frontend build)

### Testing
- Run Python tests: `pytest` -- takes 2 seconds. NEVER CANCEL. Set timeout to 60+ seconds.
- Run tests with slow/network tests: `cd recipe_estimator && pytest --runslow` -- takes 2 seconds but network tests will fail in sandboxed environment.
- Alternative: `make tests`
- **CRITICAL**: Two tests will fail due to network connectivity (`test_estimate_recipe` and `test_product_comes_from_metrics`) - this is expected in sandboxed environments.
- Frontend has no test suite configured.

### Build Times and Timeouts
- Python dependency install: 30 seconds (first time), 2 seconds (cached). Set timeout to 120+ seconds.
- Frontend npm install: 60 seconds (first time), 5 seconds (cached). Set timeout to 90+ seconds.  
- Frontend build: 20 seconds. Set timeout to 60+ seconds.
- Python tests: 2 seconds. Set timeout to 60+ seconds.
- Docker build: May fail due to npm install issues in container. Local builds work correctly.

### Key Commands Summary
```bash
# Complete setup from scratch
make install                    # Frontend build + Python deps (15-60 seconds)

# Run services  
make watch                      # Start API server (port 5521)
make watch_frontend            # Start frontend dev server (port 5522)

# Testing
make tests                     # Run Python test suite (2 seconds)
pytest                         # Same as above
cd recipe_estimator && pytest --runslow  # Include slow tests
```

## Validation

### Always Test Recipe Estimation Functionality
After making any changes to the core algorithm, always validate with this test:
```python
from recipe_estimator.recipe_estimator import estimate_recipe
product = {
    'code': 1234567890123,
    'ingredients': [
        {'id':'one', 'nutrients': {'fiber': {'percent_nom': 15, 'percent_min': 0, 'percent_max': 100}}},
        {'id':'two', 'nutrients': {'fiber': {'percent_nom': 3, 'percent_min': 0, 'percent_max': 100}}}
    ],
    'nutriments': {'fiber_100g': 10}
}
estimate_recipe(product)
# Should output ~58% for first ingredient, ~42% for second
```

### Manual Testing
- ALWAYS test both the API and frontend after making changes
- Test API endpoints using http://localhost:5521/docs 
- Test frontend functionality by visiting http://localhost:5522/#PRODUCT_CODE (e.g., #0677294998025)
- Verify static build works by accessing http://localhost:5521/static/#PRODUCT_CODE

### Expected Test Failures
- `test_estimate_recipe` and `test_product_comes_from_metrics` will fail due to network connectivity to `world.openfoodfacts.net`
- This is expected and normal in sandboxed environments
- All other 32 tests should pass

## Common Tasks

### Development Workflow
1. Always run `make install` first on a fresh clone
2. Start backend with `make watch`
3. In a separate terminal, start frontend with `make watch_frontend`  
4. Make your changes
5. Run tests with `make tests` to verify changes
6. Test manually using the validation scenarios above

### Data Processing
- Refresh ingredient taxonomy: `make refresh_ingredients_taxonomy`
- Build CIQUAL ingredients: `make build_ciqual_ingredients`
- These commands require network access to external APIs

### Docker (Limited Support)
- Docker build may fail due to npm install issues in the container environment
- Local development using the native Python/Node.js setup is recommended
- If Docker is needed, the CI system handles container builds successfully

## Code Structure

### Key Files and Directories
- `recipe_estimator/` - Main Python package containing the estimation algorithms
- `frontend/` - React TypeScript application
- `static/` - Built frontend files (created by `npm run build`)
- `requirements.txt` - Python dependencies
- `frontend/package.json` - Node.js dependencies
- `Makefile` - Common build and run commands
- `Dockerfile` - Container build (may have issues locally)

### Important Python Modules
- `recipe_estimator/main.py` - FastAPI application entry point
- `recipe_estimator/recipe_estimator.py` - Core estimation algorithm (original)
- `recipe_estimator/recipe_estimator_scipy.py` - SciPy-based optimization algorithm
- `recipe_estimator/nutrients.py` - Nutrient data preparation
- `recipe_estimator/product.py` - Product data fetching from OpenFoodFacts

### Testing Files
- All files ending in `_test.py` contain pytest test cases
- `conftest.py` - Test configuration with slow test markers
- Network-dependent tests will fail in sandboxed environments

### Configuration
- `.env` - Environment configuration including OpenFoodFacts URL
- `frontend/.env` - Frontend environment settings  
- No linting tools (black, flake8, mypy) are configured

## Troubleshooting

### Common Issues
- **Docker build fails**: Use local development setup instead
- **Network test failures**: Expected in sandboxed environments, ignore if other tests pass
- **Frontend won't start**: Ensure `npm install` completed successfully
- **API returns errors**: Check that Python dependencies are installed and backend is running
- **Static files not found**: Run `cd frontend && npm run build` to generate static files

### Performance Notes
- The recipe estimation algorithm is computationally intensive but typically completes in <1 second
- SciPy optimization is generally preferred over the original OR-Tools implementation
- Frontend build includes optimization and should be rebuilt after changes to React components

This application helps food scientists and researchers estimate ingredient proportions in processed food products using publicly available nutrient information and advanced mathematical optimization techniques.