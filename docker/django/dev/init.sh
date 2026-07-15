#!/usr/bin/env sh
set -ex

uv run manage.py migrate
uv run manage.py loaddata admins schedules

uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 5