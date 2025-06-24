refresh_ingredients_taxonomy:
	node scripts/refresh_ingredients_taxonomy.mjs

dev:
	cd ./frontend; npm install; npm run build
	pip install -r requirements.txt

up:
	uvicorn recipe_estimator.main:app --reload