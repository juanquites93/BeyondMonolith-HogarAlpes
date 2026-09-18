# -----------------------------------------------------------------------------
# Security Group para la instancia EC2 principal
# -----------------------------------------------------------------------------
resource "aws_security_group" "ec2" {
  name        = "${local.name_prefix}-ec2-sg"
  description = "Security group para la instancia EC2 de Hogar de los Alpes"
  vpc_id      = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ec2-sg"
  })
}

# Acceso SSH restringido al CIDR del administrador
resource "aws_vpc_security_group_ingress_rule" "ssh" {
  count             = var.allowed_ssh_cidr != "" ? 1 : 0
  security_group_id = aws_security_group.ec2.id
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
  cidr_ipv4         = var.allowed_ssh_cidr
  description       = "SSH desde IP administrador"
}

# Endpoints públicos de microservicios (HTTP)
resource "aws_vpc_security_group_ingress_rule" "microservices" {
  security_group_id = aws_security_group.ec2.id
  from_port         = 8000
  to_port           = 8003
  ip_protocol       = "tcp"
  cidr_ipv4         = var.allowed_api_cidr
  description       = "Endpoints HTTP de microservicios"
}

# Pulsar Admin REST API - acceso restringido (no expuesto a Internet por defecto)
resource "aws_vpc_security_group_ingress_rule" "pulsar_admin" {
  count             = var.allowed_ssh_cidr != "" ? 1 : 0
  security_group_id = aws_security_group.ec2.id
  from_port         = 8080
  to_port           = 8080
  ip_protocol       = "tcp"
  cidr_ipv4         = var.allowed_ssh_cidr
  description       = "Pulsar Admin REST API"
}

# Pulsar Binary Protocol - solo tráfico interno del security group
resource "aws_vpc_security_group_ingress_rule" "pulsar_binary_internal" {
  security_group_id            = aws_security_group.ec2.id
  from_port                    = 6650
  to_port                      = 6650
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ec2.id
  description                  = "Pulsar binary protocol interno"
}

# PostgreSQL - solo tráfico interno del security group
resource "aws_vpc_security_group_ingress_rule" "postgres_internal" {
  security_group_id            = aws_security_group.ec2.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ec2.id
  description                  = "PostgreSQL interno"
}

# Permite toda la comunicación interna entre contenedores en el mismo host
resource "aws_vpc_security_group_ingress_rule" "self_all" {
  security_group_id            = aws_security_group.ec2.id
  ip_protocol                  = "-1"
  referenced_security_group_id = aws_security_group.ec2.id
  description                  = "Todo el trafico interno del security group"
}

# Egreso completo
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.ec2.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
  description       = "Egreso completo"
}
