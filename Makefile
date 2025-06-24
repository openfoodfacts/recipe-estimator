refresh_ingredients_taxonomy:
	python scripts/refresh_ingredients_taxonomy.py

install:
	cd ./frontend; npm install; npm run build
	pip install -r requirements.txt

watch:
	uvicorn recipe_estimator.main:app --port 5521 --reload

build:
	docker compose build

up: build
	docker compose up --wait

tests:
	pytest
