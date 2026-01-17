 # syntax=docker/dockerfile:1.6
FROM python:3.14-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

RUN useradd -m botuser
COPY --chown=botuser:botuser spongebot.py spongebob_content.json ./
USER botuser

CMD ["python", "spongebot.py"]
