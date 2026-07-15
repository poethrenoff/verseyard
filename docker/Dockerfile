# Python image
FROM python:3.14.5-slim AS python-image
COPY --from=ghcr.io/astral-sh/uv:0.9.24 /uv /uvx /bin/

RUN apt-get update

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app

COPY ./pyproject.toml .
COPY ./uv.lock .
RUN uv sync

COPY ./src .

# Django image
FROM python-image AS django-image
RUN uv run manage.py collectstatic --no-input

# Nginx image
FROM nginx:1.31.0-alpine3.23 AS nginx-image
COPY --from=django-image /app/static /app/static
COPY ./docker/web/default.conf /etc/nginx/conf.d/default.conf
