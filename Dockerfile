FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the standard port (Render or other PaaS often override this via the PORT env var)
EXPOSE 8000

# Start FastAPI application
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
