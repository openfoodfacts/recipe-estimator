refresh_ingredients_taxonomy:
	python scripts/refresh_ingredients_taxonomy.py

build_ciqual_ingredients:
	python -m scripts.build_ciqual_ingredients

install:
	cd ./frontend; npm install; npm run build
	pip install -r requirements.txt

watch:
	uvicorn recipe_estimator.main:app --port 5521 --reload

watch_frontend:
	cd ./frontend; npm start

build:
	docker compose build

up: build
	docker compose up --wait

tests:
	pytest ${args}
