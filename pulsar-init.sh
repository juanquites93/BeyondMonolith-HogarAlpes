#!/bin/bash
set -e

echo "Esperando a que Pulsar esté listo..."
sleep 15

echo "Creando tenant hogar..."
bin/pulsar-admin tenants create hogar || true

echo "Creando namespace hogar/alpes..."
bin/pulsar-admin namespaces create hogar/alpes || true

echo "Habilitando auto-creación de tópicos..."
bin/pulsar-admin namespaces set-auto-topic-creation --enable hogar/alpes || true

echo "Pulsar init completado"
