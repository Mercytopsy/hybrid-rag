# One image, two uses:
#   - API server (default):  docker compose up  (runs the CMD below)
#   - CLI indexer (one-off): docker run ... <image> python main.py /data/report.pdf
#                             (overrides CMD, same image/deps, no second Dockerfile needed)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
