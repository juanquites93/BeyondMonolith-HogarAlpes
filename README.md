# Infraestructura AWS para Hogar de los Alpes

Este directorio contiene la infraestructura como código (Terraform) para desplegar los microservicios de **Hogar de los Alpes** en Amazon Web Services (AWS), ejecutándose en instancias EC2 con Docker y Docker Compose.

---

## 1. Arquitectura implementada

La solución despliega todos los servicios en **una instancia EC2** dentro de una VPC dedicada. Se eligió esta aproximación para un entorno de desarrollo/pruebas por simplicidad operativa y costo, sin sacrificar persistencia ni networking adecuada.

### Componentes principales

```text
AWS
│
├── VPC (10.0.0.0/16)
│   ├── Subnets públicas (2 AZ)
│   ├── Internet Gateway
│   └── Route Tables
│
├── Security Groups (mínimo acceso)
│
├── IAM Role + Instance Profile
│   └── Políticas: SSM, EBS, Secrets Manager
│
├── S3 Bucket (archivos de despliegue)
│
├── Secrets Manager (contraseña PostgreSQL)
│
├── EBS Volumes (persistencia)
│   ├── /data/pulsar   →  Apache Pulsar
│   └── /data/postgres →  PostgreSQL
│
└── EC2 Instance (Ubuntu 22.04)
    ├── Docker + Docker Compose
    ├── Apache Pulsar Cluster (5 contenedores)
    │   ├── pulsar-zookeeper
    │   ├── pulsar-bookie-1
    │   ├── pulsar-bookie-2
    │   ├── pulsar-broker-1  (expone 6650/8080)
    │   └── pulsar-broker-2  (expone 6651/8081)
    │
    ├── PostgreSQL independiente (4 contenedores)
    │   ├── marketplace-postgres    → marketplace_db
    │   ├── verificacion-postgres   → verificacion_db
    │   ├── cotizacion-postgres     → cotizacion_db
    │   └── notificaciones-postgres → notificaciones_db
    │
    └── Microservicios (4 contenedores)
        ├── marketplace    :8000
        ├── verificacion   :8001
        ├── cotizacion     :8002
        └── notificaciones :8003
```

### Distribución en una sola EC2

Se utiliza una sola instancia EC2 porque:

- Todos los servicios ya están diseñados para comunicarse por nombres de host dentro de una red Docker bridge.
- Para un entorno de desarrollo/pruebas, una sola instancia reduce costos y complejidad de networking.
- El tipo de instancia por defecto es `t3.xlarge` (4 vCPU, 16 GB RAM), suficiente para:
  - 5 contenedores de Pulsar (~3-4 GB RAM configurados).
  - 4 contenedores PostgreSQL (~1-2 GB RAM).
  - 4 microservicios Python (~1-2 GB RAM).
  - Overhead de Docker y del sistema operativo.

Si en el futuro se requiere alta disponibilidad o mayor capacidad, se recomienda:

1. Separar Pulsar en una o más EC2 dedicadas.
2. Separar PostgreSQL en EC2 dedicadas (o evaluar Amazon RDS si la restricción de contenedores cambia).
3. Distribuir los microservicios en un cluster ECS/EKS con Auto Scaling.

---

## 2. Diagrama de componentes

```text
                                    Internet
                                       │
                                       ▼
                               [Elastic IP: EC2]
                                       │
                    ┌──────────────────┼──────────────────┐
                    │      EC2 Instance (Docker Host)     │
                    │                                     │
                    │  ┌─────────────────────────────┐   │
                    │  │   Apache Pulsar Cluster     │   │
                    │  │  - ZooKeeper                │   │
                    │  │  - Bookie 1, Bookie 2       │   │
                    │  │  - Broker 1, Broker 2       │   │
                    │  └─────────────────────────────┘   │
                    │                                     │
                    │  ┌─────────────────────────────┐   │
                    │  │  PostgreSQL (4 instancias)  │   │
                    │  │  marketplace / verificacion │   │
                    │  │  cotizacion / notificaciones│   │
                    │  └─────────────────────────────┘   │
                    │                                     │
                    │  ┌─────────────────────────────┐   │
                    │  │  Microservicios (4)         │   │
                    │  │  marketplace:8000           │   │
                    │  │  verificacion:8001          │   │
                    │  │  cotizacion:8002            │   │
                    │  │  notificaciones:8003        │   │
                    │  └─────────────────────────────┘   │
                    │                                     │
                    │  Volumes EBS:                       │
                    │    /data/pulsar                     │
                    │    /data/postgres                   │
                    └─────────────────────────────────────┘
```

---

## 3. Requisitos previos

- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5.0
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configurado
- Una cuenta de AWS con permisos para crear: VPC, EC2, EBS, IAM, S3, Secrets Manager

---

## 4. Configurar AWS credentials

Opción A: variables de entorno

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"
```

Opción B: perfil de AWS CLI

```bash
aws configure --profile hogar-alpes
export AWS_PROFILE=hogar-alpes
```

Opción C: AWS SSO

```bash
aws sso login --profile hogar-alpes
export AWS_PROFILE=hogar-alpes
```

---

## 5. Configurar variables de Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edita `terraform.tfvars` y ajusta como mínimo:

```hcl
# REEMPLAZA con tu IP pública real para restringir acceso SSH/API
allowed_ssh_cidr = "203.0.113.10/32"
allowed_api_cidr = "203.0.113.10/32"

# Opcional: key pair para SSH. Si se omite, se usa AWS Systems Manager Session Manager.
# key_pair_name = "mi-key-pair"
```

> **Seguridad:** no commitees `terraform.tfvars` con valores reales. El archivo está ignorado por `.gitignore`.

---

## 6. Ejecutar Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

El despliegue completo toma entre **8 y 15 minutos**, dependiendo principalmente del tiempo que Docker tarde en construir las imágenes de los microservicios.

---

## 7. Conectarse a la EC2

### Opción A: AWS Systems Manager Session Manager (recomendado si no configuraste key pair)

```bash
aws ssm start-session --target $(terraform output -raw ec2_instance_id)
```

### Opción B: SSH con key pair

```bash
ssh -i ~/.ssh/mi-key-pair.pem ubuntu@$(terraform output -raw ec2_public_ip)
```

### Verificar logs de bootstrap

```bash
sudo tail -f /var/log/hogar-alpes-bootstrap.log
```

---

## 8. Cómo levantar los servicios

Los servicios se levantan automáticamente mediante `user_data` al arrancar la EC2. Si necesitas reiniciarlos manualmente:

```bash
sudo su -
cd /opt/hogar-alpes
docker compose -f docker-compose.aws.yml up -d --build
```

Para ver el estado:

```bash
cd /opt/hogar-alpes
docker compose -f docker-compose.aws.yml ps
```

---

## 9. Verificar Apache Pulsar

Desde tu máquina local (reemplaza `<EC2_IP>` por la IP pública):

```bash
# Health check del broker
curl http://<EC2_IP>:8080/admin/v2/brokers/health

# Listar tenants
curl http://<EC2_IP>:8080/admin/v2/tenants

# Listar namespaces del tenant hogar
curl http://<EC2_IP>:8080/admin/v2/namespaces/hogar
```

Desde dentro de la EC2:

```bash
cd /opt/hogar-alpes
docker exec -it hogar_alpes_pulsar_broker_1 bin/pulsar-admin tenants list
docker exec -it hogar_alpes_pulsar_broker_1 bin/pulsar-admin namespaces list hogar
docker exec -it hogar_alpes_pulsar_broker_1 bin/pulsar-admin topics list hogar/alpes
```

---

## 10. Verificar PostgreSQL

Desde dentro de la EC2:

```bash
# marketplace
docker exec -it hogar_alpes_marketplace_postgres psql -U hogar -d marketplace_db -c "\l"

# verificacion
docker exec -it hogar_alpes_verificacion_postgres psql -U hogar -d verificacion_db -c "\dt"

# cotizacion
docker exec -it hogar_alpes_cotizacion_postgres psql -U hogar -d cotizacion_db -c "\dt"

# notificaciones
docker exec -it hogar_alpes_notificaciones_postgres psql -U hogar -d notificaciones_db -c "\dt"
```

---

## 11. Consultar logs

```bash
cd /opt/hogar-alpes

# Todos los servicios
docker compose -f docker-compose.aws.yml logs -f

# Servicio específico
docker compose -f docker-compose.aws.yml logs -f marketplace
docker compose -f docker-compose.aws.yml logs -f pulsar-broker-1
docker compose -f docker-compose.aws.yml logs -f marketplace-postgres
```

---

## 12. Actualizar los servicios

1. Actualiza el código fuente localmente.
2. Vuelve a ejecutar Terraform para regenerar y subir el zip:

```bash
cd terraform
terraform apply
```

3. Conéctate a la EC2 y fuerza la reconstrucción:

```bash
cd /opt/hogar-alpes
docker compose -f docker-compose.aws.yml pull
docker compose -f docker-compose.aws.yml up -d --build
```

> Nota: Terraform regenera automáticamente `hogar-alpes-project.zip` cuando cambian los archivos del proyecto gracias al `etag` basado en `md5`.

---

## 13. Destruir la infraestructura

```bash
cd terraform
terraform destroy
```

> **Advertencia:** `terraform destroy` elimina la instancia EC2 y los volúmenes EBS adjuntos. Los datos de PostgreSQL y Pulsar se perderán a menos que hayas creado snapshots de los volúmenes.

---

## 14. Puertos expuestos

| Puerto | Servicio | Acceso público | Descripción |
|--------|----------|----------------|-------------|
| 22 | SSH | Solo `allowed_ssh_cidr` | Acceso administrativo |
| 8000 | marketplace | `allowed_api_cidr` | API REST ms-marketplace-asignacion |
| 8001 | verificacion | `allowed_api_cidr` | API REST ms-verificacion-acreditacion |
| 8002 | cotizacion | `allowed_api_cidr` | API REST generador_cotizacion |
| 8003 | notificaciones | `allowed_api_cidr` | API REST ms-notificaciones |
| 8080 | Pulsar Admin API | Solo `allowed_ssh_cidr` | Admin REST API del broker 1 |
| 6650 | Pulsar Binary | Solo interno/EC2 | Protocolo binario Pulsar |
| 6651, 8081 | Pulsar broker 2 | Solo interno | Segundo broker (no expuesto a Internet) |
| 5432 | PostgreSQL | Solo interno | Acceso interno entre contenedores |

---

## 15. Recursos AWS creados

- 1 VPC
- 2 subnets públicas
- 1 Internet Gateway
- 1 route table pública
- 1 Security Group
- 1 IAM Role + Instance Profile
- 2 IAM Policies personalizadas
- 1 Secret en AWS Secrets Manager
- 1 S3 Bucket (versionado y cifrado)
- 1 Elastic IP
- 1 instancia EC2
- 2 volúmenes EBS adicionales (Pulsar y PostgreSQL)

---

## 16. Costos aproximados

Estimación para la región `us-east-1` (puede variar, ver [AWS Pricing Calculator](https://calculator.aws/)):

| Recurso | Especificación | Costo mensual aprox. |
|---------|----------------|----------------------|
| EC2 `t3.xlarge` | 4 vCPU, 16 GB | ~$120 USD |
| EBS root (30 GB gp3) | Incluido en instancia | ~$2.40 USD |
| EBS Pulsar (50 GB gp3) | Persistencia Pulsar | ~$4.00 USD |
| EBS PostgreSQL (30 GB gp3) | Persistencia DBs | ~$2.40 USD |
| Elastic IP | 1 asociado a instancia en uso | Gratis |
| S3 | ~5 MB | ~$0.01 USD |
| Secrets Manager | 1 secret | ~$0.40 USD |
| Data transfer | Saliente mínimo | Variable |

**Total estimado: ~$130 USD/mes** (sin considerar impuestos ni transferencia de datos significativa).

Para reducir costos en desarrollo:

- Usa `t3.large` (2 vCPU, 8 GB) si la carga es muy baja, aunque puede quedar corta con todos los contenedores.
- Apaga la instancia fuera de horario laboral.
- Reduce el tamaño de los volúmenes EBS.

---

## 17. Decisiones de diseño e inconsistencias resueltas

### Inconsistencias detectadas

1. **PostgreSQL compartido vs. independiente**: `docker-compose.yml` original usa un solo PostgreSQL con 4 bases de datos. El requisito del usuario exige 1 PostgreSQL por microservicio. Se implementaron 4 contenedores PostgreSQL independientes.
2. **Apache Pulsar standalone vs. cluster**: El `docker-compose.yml` original usa `bin/pulsar standalone` (1 contenedor). El requisito exige 5 contenedores coherentes. Se implementó un cluster con 1 ZooKeeper + 2 Bookies + 2 Brokers, basado en la [documentación oficial de Pulsar 3.2.x](https://pulsar.apache.org/docs/3.2.x/getting-started-docker-compose/).
3. **Puerto de notificaciones**: El Dockerfile de `ms-notificaciones` expone el 8000, pero `docker-compose.yml` lo mapea externamente al 8003. Se mantiene ese mapeo en `docker-compose.aws.yml`.
4. **Credenciales hardcodeadas**: El `docker-compose.yml` original tiene `POSTGRES_PASSWORD: alpes`. En AWS se externalizó a AWS Secrets Manager y se inyecta mediante `user_data`.

### Decisiones adicionales

- **Una sola EC2**: elegida por simplicidad y costo para un entorno de desarrollo/pruebas.
- **EBS persistente**: se usan 2 volúmenes EBS (`/data/pulsar` y `/data/postgres`) montados como bind mounts, en lugar de volúmenes Docker anónimos.
- **S3 para distribución de código**: el proyecto se empaqueta en un zip y se sube a S3 para que `user_data` lo descargue y descomprima en la EC2. Esto evita depender de un repositorio Git específico.
- **SSM Session Manager**: se recomienda como método de conexión para no exponer SSH a Internet innecesariamente.

---

## 18. Solución de problemas

### Los contenedores no arrancan

```bash
sudo tail -f /var/log/hogar-alpes-bootstrap.log
cd /opt/hogar-alpes
docker compose -f docker-compose.aws.yml ps
docker compose -f docker-compose.aws.yml logs --tail=100 pulsar-broker-1
```

### Pulsar no inicializa el tenant

```bash
docker exec -it hogar_alpes_pulsar_broker_1 bin/pulsar-admin --admin-url http://localhost:8080 brokers healthcheck
docker exec -it hogar_alpes_pulsar_broker_1 bin/pulsar-admin tenants list
```

### PostgreSQL no responde

```bash
docker exec -it hogar_alpes_marketplace_postgres pg_isready -U hogar -d marketplace_db
```

---

## 19. Estructura de archivos entregados

```text
BeyondMonolith-HogarAlpes/
├── docker-compose.aws.yml          # Docker Compose adaptado para AWS
├── .env.example                    # Variables de entorno de ejemplo
├── README.md                       # Este archivo
│
└── terraform/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── providers.tf
    ├── versions.tf
    ├── networking.tf
    ├── security_groups.tf
    ├── ec2.tf
    ├── iam.tf
    ├── storage.tf
    ├── locals.tf
    ├── terraform.tfvars.example
    └── templates/
        └── bootstrap.sh.tpl        # Script de user_data para la EC2
```

---

**Autor:** Equipo de desarrollo Hogar de los Alpes  
**Versión:** 1.0  
**Fecha:** 2026
