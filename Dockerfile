ARG USER_UID=1000
ARG USER_GID=$USER_UID

FROM node:current-alpine AS frontend-build
WORKDIR /app
COPY frontend/package* ./
RUN npm install
COPY frontend ./
RUN npm run build

FROM python:3.11-slim-buster
ARG USER_UID
ARG USER_GID
ENV PIP_CACHE_DIR=/var/cache/pip \
    PYTHON_PATH=/app
# create off user
RUN groupadd -g $USER_GID off && \
    useradd -u $USER_UID -g off -m off && \
    mkdir /app && \
    chown -R off:off /app
WORKDIR /app
COPY requirements.txt requirements.txt
RUN --mount=type=cache,id=pip-cache,target=/var/cache/pip pip3 install -r requirements.txt
COPY --chown=off:off recipe_estimator ./recipe_estimator
COPY --chown=off:off --from=frontend-build app/build ./static
USER off:off

CMD [ "uvicorn", "recipe_estimator.main:app", "--host", "0.0.0.0", "--port", "5521"]