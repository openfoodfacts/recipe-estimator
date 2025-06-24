FROM node:current-alpine AS frontend-build
WORKDIR /app
COPY frontend/package* ./
RUN npm install
COPY frontend ./
RUN npm run build

FROM python:3.10-slim-buster
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY recipe_estimator ./recipe_estimator
COPY --from=frontend-build app/build ./static

CMD [ "uvicorn", "recipe_estimator.main:app", "--host", "0.0.0.0", "--port", "5521"]