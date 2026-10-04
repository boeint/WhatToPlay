# WhatToPlay container image.
# Configuration comes from environment variables (see .env.example).
FROM python:3.14-slim

# Don't write .pyc files; print logs immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Libraries first: this layer is reused between builds while requirements.txt doesn't change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Run as an unprivileged user, not root.
RUN useradd --system --no-create-home --uid 10001 whattoplay
USER whattoplay

EXPOSE 8000

# Unraid / Docker show the container as healthy only when the app answers
# and can reach its database.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

CMD ["start.sh"]
