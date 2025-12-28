FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (optional but useful for timezone, certificates)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tzdata \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application sources.
# NOTE: Keep this list explicit to avoid copying local secrets into the image.
COPY bot.py /app/bot.py
COPY task_manager.py /app/task_manager.py
COPY runtime_settings.py /app/runtime_settings.py

CMD ["python", "/app/bot.py"]
