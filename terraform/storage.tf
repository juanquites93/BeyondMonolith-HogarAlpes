# -----------------------------------------------------------------------------
# Volumen EBS para datos de Apache Pulsar
# -----------------------------------------------------------------------------
resource "aws_ebs_volume" "pulsar" {
  availability_zone = var.availability_zones[0]
  size              = var.pulsar_ebs_volume_size
  encrypted         = true
  type              = "gp3"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-pulsar-data"
  })
}

# -----------------------------------------------------------------------------
# Volumen EBS para datos de PostgreSQL
# -----------------------------------------------------------------------------
resource "aws_ebs_volume" "postgres" {
  availability_zone = var.availability_zones[0]
  size              = var.postgres_ebs_volume_size
  encrypted         = true
  type              = "gp3"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres-data"
  })
}

# -----------------------------------------------------------------------------
# Adjuntar volúmenes a la instancia EC2
# Se realiza en ec2.tf mediante aws_volume_attachment
# -----------------------------------------------------------------------------
