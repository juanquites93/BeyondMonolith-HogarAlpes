FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY pyproject.toml .
RUN pip install -e .

EXPOSE 8000

# PORT es configurable por variable de entorno (default 8000, igual que antes).
# Forma "shell" en vez de exec para que ${PORT} se expanda al arrancar.
CMD uvicorn notificaciones.main:app --host 0.0.0.0 --port ${PORT:-8000}
