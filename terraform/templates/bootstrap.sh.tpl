#!/bin/bash
set -e
set -o pipefail

exec > >(tee /var/log/hogar-alpes-bootstrap.log) 2>&1

echo "=== Bootstrap iniciado: $(date) ==="

# -----------------------------------------------------------------------------
# 1. Actualizar sistema e instalar dependencias
# -----------------------------------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  apt-transport-https \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  jq \
  awscli \
  net-tools \
  xfsprogs \
  unzip

# -----------------------------------------------------------------------------
# 2. Instalar Docker y Docker Compose plugin
# -----------------------------------------------------------------------------
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

usermod -aG docker ubuntu
systemctl enable docker
systemctl start docker

# -----------------------------------------------------------------------------
# 3. Detectar y montar volúmenes EBS
# -----------------------------------------------------------------------------
# Las instancias Nitro usan nombres NVMe (/dev/nvme*). Se detectan por tamaño.
PULSAR_SIZE_GB=${pulsar_volume_size_gb}
POSTGRES_SIZE_GB=${postgres_volume_size_gb}

# Esperar a que los volúmenes aparezcan
sleep 10

# Función para obtener tamaño en GB de un dispositivo
device_size_gb() {
  lsblk -d -b -n -o SIZE "$1" 2>/dev/null | awk '{print int($1/1024/1024/1024)}'
}

# Detectar dispositivos EBS candidatos (discos no montados como root)
mapfile -t CANDIDATES < <(lsblk -d -p -n -o NAME,TYPE,MOUNTPOINT | awk '$2=="disk" && $3=="" {print $1}')

PULSAR_DEVICE=""
POSTGRES_DEVICE=""

for dev in "$${CANDIDATES[@]}"; do
  size=$(device_size_gb "$dev")
  echo "Dispositivo candidato: $dev -> $${size} GB"

  # Tolerancia: el tamaño reportado puede variar ligeramente
  if [ "$size" -ge $((PULSAR_SIZE_GB - 2)) ] && [ "$size" -le $((PULSAR_SIZE_GB + 2)) ] && [ -z "$PULSAR_DEVICE" ]; then
    PULSAR_DEVICE="$dev"
  elif [ "$size" -ge $((POSTGRES_SIZE_GB - 2)) ] && [ "$size" -le $((POSTGRES_SIZE_GB + 2)) ] && [ -z "$POSTGRES_DEVICE" ]; then
    POSTGRES_DEVICE="$dev"
  fi
done

# Fallback para instancias no Nitro con nombres clásicos
if [ -z "$PULSAR_DEVICE" ] && [ -e /dev/xvdf ]; then
  PULSAR_DEVICE="/dev/xvdf"
fi
if [ -z "$POSTGRES_DEVICE" ] && [ -e /dev/xvdg ]; then
  POSTGRES_DEVICE="/dev/xvdg"
fi

if [ -z "$PULSAR_DEVICE" ] || [ -z "$POSTGRES_DEVICE" ]; then
  echo "ERROR: No se pudieron detectar los volúmenes EBS"
  echo "Pulsar device: $PULSAR_DEVICE"
  echo "Postgres device: $POSTGRES_DEVICE"
  lsblk
  exit 1
fi

echo "Pulsar device: $PULSAR_DEVICE"
echo "Postgres device: $POSTGRES_DEVICE"

# Formatear si no tienen filesystem
if ! file -s "$PULSAR_DEVICE" | grep -q filesystem; then
  echo "Formateando $PULSAR_DEVICE con xfs"
  mkfs -t xfs "$PULSAR_DEVICE"
fi

if ! file -s "$POSTGRES_DEVICE" | grep -q filesystem; then
  echo "Formateando $POSTGRES_DEVICE con xfs"
  mkfs -t xfs "$POSTGRES_DEVICE"
fi

# Montar Pulsar
mkdir -p /data/pulsar
mount "$PULSAR_DEVICE" /data/pulsar
uuid=$(blkid -s UUID -o value "$PULSAR_DEVICE")
echo "UUID=$uuid /data/pulsar xfs defaults,nofail 0 2" >> /etc/fstab

# Montar PostgreSQL
mkdir -p /data/postgres
mount "$POSTGRES_DEVICE" /data/postgres
uuid=$(blkid -s UUID -o value "$POSTGRES_DEVICE")
echo "UUID=$uuid /data/postgres xfs defaults,nofail 0 2" >> /etc/fstab

# Crear subdirectorios para cada servicio
mkdir -p /data/pulsar/zookeeper
mkdir -p /data/pulsar/bookie-1
mkdir -p /data/pulsar/bookie-2
mkdir -p /data/pulsar/broker-1
mkdir -p /data/pulsar/broker-2

mkdir -p /data/postgres/marketplace
mkdir -p /data/postgres/verificacion
mkdir -p /data/postgres/cotizacion
mkdir -p /data/postgres/notificaciones
mkdir -p /data/postgres/orquestador

# Ajustar permisos para contenedores (Pulsar usa uid 10000)
chown -R 10000:10000 /data/pulsar
chmod -R 750 /data/pulsar

chown -R 999:999 /data/postgres
chmod -R 700 /data/postgres

# -----------------------------------------------------------------------------
# 4. Descargar y extraer el proyecto desde S3
# -----------------------------------------------------------------------------
DEPLOY_DIR="/opt/hogar-alpes"
mkdir -p "$DEPLOY_DIR"
aws s3 cp "s3://${s3_bucket}/deploy/hogar-alpes-project.zip" /tmp/hogar-alpes-project.zip
unzip -o /tmp/hogar-alpes-project.zip -d "$DEPLOY_DIR"
rm -f /tmp/hogar-alpes-project.zip

# -----------------------------------------------------------------------------
# 5. Crear archivo .env con secrets y configuración
# -----------------------------------------------------------------------------
echo "Obteniendo secretos desde AWS Secrets Manager..."
POSTGRES_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id ${postgres_secret_name} \
  --query SecretString \
  --output text)

cat > "$DEPLOY_DIR/.env" <<EOF
POSTGRES_USER=${postgres_user}
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
PULSAR_CLUSTER_NAME=${pulsar_cluster_name}
PULSAR_SERVICE_URL=pulsar://pulsar-broker-1:6650
EOF

chmod 600 "$DEPLOY_DIR/.env"

# -----------------------------------------------------------------------------
# 6. Levantar contenedores
# -----------------------------------------------------------------------------
cd "$DEPLOY_DIR"

echo "Construyendo imágenes y levantando servicios..."
docker compose -f ${docker_compose_file} pull || true
docker compose -f ${docker_compose_file} up -d --build

# -----------------------------------------------------------------------------
# 7. Health check final
# -----------------------------------------------------------------------------
echo "Esperando a que los servicios estén saludables..."
sleep 30

docker compose -f ${docker_compose_file} ps

echo "=== Bootstrap finalizado: $(date) ==="
