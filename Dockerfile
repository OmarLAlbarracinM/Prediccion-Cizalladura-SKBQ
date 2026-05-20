FROM python:3.11-slim

WORKDIR /app

# System deps for numpy/pandas/tensorflow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
ENV AIRPORT_CODE=SKBO
ENV MODEL_PATH=models/best_model_20h.h5
ENV LOG_LEVEL=info

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --log-level ${LOG_LEVEL}"]
