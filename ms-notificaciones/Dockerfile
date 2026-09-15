FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY pyproject.toml .
RUN pip install -e .

EXPOSE 8000

CMD ["uvicorn", "notificaciones.main:app", "--host", "0.0.0.0", "--port", "8000"]
