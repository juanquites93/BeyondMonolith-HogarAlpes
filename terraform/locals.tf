locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  name_prefix = "${var.project_name}-${var.environment}"

  # Rutas de montaje para volúmenes EBS
  pulsar_data_path   = "/data/pulsar"
  postgres_data_path = "/data/postgres"

  # Credenciales de PostgreSQL
  postgres_user     = var.postgres_admin_user
  postgres_password = var.postgres_admin_password != "" ? var.postgres_admin_password : random_password.postgres_admin_password[0].result

  # Configuración de Pulsar
  pulsar_image = "apachepulsar/pulsar:3.2.0"

  # Lista de microservicios con sus puertos y bases de datos
  microservicios = {
    marketplace = {
      build_dir = "ms-marketplace-asignacion"
      host_port = 8000
      db_name   = "marketplace_db"
    }
    verificacion = {
      build_dir = "ms-verificacion-acreditacion"
      host_port = 8001
      db_name   = "verificacion_db"
    }
    cotizacion = {
      build_dir = "generador_cotizacion"
      host_port = 8002
      db_name   = "cotizacion_db"
    }
    notificaciones = {
      build_dir = "ms-notificaciones"
      host_port = 8003
      db_name   = "notificaciones_db"
    }
  }
}

# Contraseña aleatoria para PostgreSQL si no se proporciona una
resource "random_password" "postgres_admin_password" {
  count   = var.postgres_admin_password != "" ? 0 : 1
  length  = 24
  special = false
}
