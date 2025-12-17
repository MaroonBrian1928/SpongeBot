FROM python:3.14-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m botuser
COPY --chown=botuser:botuser spongebot.py spongebob_content.json ./
USER botuser

CMD ["python", "spongebot.py"]
