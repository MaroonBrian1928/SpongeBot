# syntax=docker/dockerfile:1.6
FROM python:3.14-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /uvx /bin/

COPY pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

# RUN useradd -m botuser
RUN groupadd -r botuser && useradd -r -g botuser -d /home/botuser -m botuser
COPY --chown=botuser:botuser spongebot.py spongebob_content.json ./
USER botuser

CMD [".venv/bin/python", "spongebot.py"]
