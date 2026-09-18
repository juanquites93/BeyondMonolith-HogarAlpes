# -----------------------------------------------------------------------------
# Variables generales del proyecto
# -----------------------------------------------------------------------------
variable "aws_region" {
  description = "Región de AWS donde se desplegará la infraestructura"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nombre del proyecto para etiquetado de recursos"
  type        = string
  default     = "hogar-alpes"
}

variable "environment" {
  description = "Ambiente de despliegue (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# -----------------------------------------------------------------------------
# Networking
# -----------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block para la VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Lista de CIDRs para subnets públicas"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "availability_zones" {
  description = "Zonas de disponibilidad a utilizar"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# -----------------------------------------------------------------------------
# Acceso y seguridad
# -----------------------------------------------------------------------------
variable "allowed_ssh_cidr" {
  description = "CIDR permitido para acceso SSH (tu IP pública recomendada)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "allowed_api_cidr" {
  description = "CIDR permitido para acceso a los endpoints públicos de microservicios"
  type        = string
  default     = "0.0.0.0/0"
}

variable "key_pair_name" {
  description = "Nombre del key pair de AWS para acceso SSH. Si se deja vacío se usará SSM Session Manager."
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Instancia EC2
# -----------------------------------------------------------------------------
variable "ec2_instance_type" {
  description = "Tipo de instancia EC2. Se recomienda t3.xlarge o superior para todos los contenedores."
  type        = string
  default     = "t3.xlarge"
}

variable "ec2_root_volume_size" {
  description = "Tamaño en GB del volumen raíz de la EC2"
  type        = number
  default     = 30
}

variable "ec2_ami" {
  description = "AMI de Ubuntu 22.04 LTS. Si se deja vacío se usa la AMI más reciente."
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Almacenamiento EBS para datos persistentes
# -----------------------------------------------------------------------------
variable "pulsar_ebs_volume_size" {
  description = "Tamaño en GB del volumen EBS para datos de Apache Pulsar"
  type        = number
  default     = 50
}

variable "postgres_ebs_volume_size" {
  description = "Tamaño en GB del volumen EBS para datos de PostgreSQL"
  type        = number
  default     = 30
}

# -----------------------------------------------------------------------------
# Credenciales y secrets
# -----------------------------------------------------------------------------
variable "postgres_admin_user" {
  description = "Usuario administrador para todas las instancias PostgreSQL"
  type        = string
  default     = "hogar"
}

variable "postgres_admin_password" {
  description = "Contraseña del usuario administrador de PostgreSQL. Se genera automáticamente si se deja vacío."
  type        = string
  default     = ""
  sensitive   = true
}

variable "pulsar_cluster_name" {
  description = "Nombre del cluster de Apache Pulsar"
  type        = string
  default     = "hogar-alpes-cluster"
}

# -----------------------------------------------------------------------------
# Despliegue de aplicación
# -----------------------------------------------------------------------------
variable "app_repository_url" {
  description = "URL del repositorio Git para clonar en la EC2. Si se deja vacío se copia el proyecto actual mediante S3."
  type        = string
  default     = ""
}

variable "app_repository_branch" {
  description = "Rama del repositorio a clonar"
  type        = string
  default     = "main"
}

variable "docker_compose_file" {
  description = "Nombre del archivo docker-compose a utilizar en la EC2"
  type        = string
  default     = "docker-compose.aws.yml"
}
