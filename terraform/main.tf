# =============================================================================
# Infraestructura AWS para Hogar de los Alpes
# =============================================================================
# Este directorio despliega:
#   - VPC, subnets públicas, Internet Gateway y route tables
#   - Security Groups con mínimo acceso
#   - IAM Roles/Policies para EC2
#   - Volúmenes EBS persistentes para Pulsar y PostgreSQL
#   - Instancia EC2 con Docker, Docker Compose y los contenedores de la app
#   - S3 bucket para archivos de despliegue
#   - AWS Secrets Manager para la contraseña de PostgreSQL
#
# Los recursos están organizados en archivos temáticos:
#   - networking.tf        : VPC, subnets, IGW, route tables
#   - security_groups.tf   : Security Groups
#   - iam.tf               : IAM roles, policies y Secrets Manager
#   - storage.tf           : Volúmenes EBS
#   - ec2.tf               : Instancia EC2, S3, user_data
#   - outputs.tf           : Outputs útiles
#   - variables.tf         : Variables configurables
#   - locals.tf            : Valores locales y secrets generados
#   - versions.tf          : Versiones de Terraform/providers
#   - providers.tf         : Configuración del provider AWS
# =============================================================================

# Nota: los recursos reales se definen en los archivos mencionados arriba.
