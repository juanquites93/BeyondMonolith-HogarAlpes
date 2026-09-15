#!/bin/bash
export DATABASE_URL="postgresql://hogar:alpes123@localhost:5432/marketplace"
cd /home/sebastian-betancourh/Documentos/uniandes/BeyondMonolith-HogarAlpes/marketplace_asignacion
source .venv/bin/activate
exec uvicorn marketplace_asignacion.main:app --host 0.0.0.0 --port 8001
