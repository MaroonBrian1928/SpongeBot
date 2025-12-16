FROM python:3.14-slim

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY spongebot.py spongebob_content.json ./

# Don't run as root
RUN useradd -m botuser
USER botuser

CMD ["python", "spongebot.py"]