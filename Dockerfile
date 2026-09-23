FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data

RUN chown -R app:app /app
USER app

HEALTHCHECK --interval=1m --timeout=10s --start-period=30s --retries=3 \
  CMD python -m app.healthcheck || exit 1

CMD ["python", "-m", "app.main"]

