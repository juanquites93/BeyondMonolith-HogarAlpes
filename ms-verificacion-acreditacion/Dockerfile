FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY pyproject.toml .
RUN pip install -e .

EXPOSE 8001

CMD ["uvicorn", "verificacion_acreditacion.main:app", "--host", "0.0.0.0", "--port", "8001"]
