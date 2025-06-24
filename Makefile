refresh_ingredients_taxonomy:
	python scripts/refresh_ingredients_taxonomy.py

dev:
	cd ./frontend; npm install; npm run build
	pip install -r requirements.txt

up:
	uvicorn recipe_estimator.main:app --reload