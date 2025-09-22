# Installation Guide

## Prerequisites

- Python 3.8+ 
- Node.js 16+ (for frontend development)
- Docker (optional, for containerized deployment)

## Frontend Setup

This is a create-react-app project.

To set up the frontend:

```bash
cd ./frontend
npm install
npm run build
```

This creates the static folder in the backend so that static files can be served by FastAPI. (Path is set in the .env file)

## Backend Setup

This project uses Python 3.

1. Create a virtual environment:
   ```bash
   python -m venv venv 
   ```

2. Activate the virtual environment:
   - Windows: `venv/Scripts/activate`
   - Linux/macOS: `source venv/bin/activate`

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Install (Both Frontend and Backend)

Use the provided Makefile command:
```bash
make install
```

This will install both frontend and backend dependencies and build the frontend.

## Data Setup

If you need to refresh the ingredients taxonomy:
```bash
make refresh_ingredients_taxonomy
```

If the `nutrient_map.csv` or any of the source CIQUAL XML files are updated, run:
```bash
make build_ciqual_ingredients
```

This will update the `ciqual_ingredients.json` file.