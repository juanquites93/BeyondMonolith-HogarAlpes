# -----------------------------------------------------------------------------
# Outputs de Terraform
# -----------------------------------------------------------------------------
output "ec2_public_ip" {
  description = "Dirección IP pública de la instancia EC2 (Elastic IP)"
  value       = aws_eip.ec2.public_ip
}

output "ec2_private_ip" {
  description = "Dirección IP privada de la instancia EC2"
  value       = aws_instance.main.private_ip
}

output "ec2_instance_id" {
  description = "ID de la instancia EC2"
  value       = aws_instance.main.id
}

output "vpc_id" {
  description = "ID de la VPC creada"
  value       = aws_vpc.main.id
}

output "subnet_ids" {
  description = "IDs de las subnets públicas"
  value       = aws_subnet.public[*].id
}

output "security_group_ids" {
  description = "IDs de los security groups creados"
  value       = [aws_security_group.ec2.id]
}

output "s3_deploy_bucket" {
  description = "Nombre del bucket S3 con archivos de despliegue"
  value       = aws_s3_bucket.deploy.bucket
}

output "postgres_secret_arn" {
  description = "ARN del secret de PostgreSQL en Secrets Manager"
  value       = aws_secretsmanager_secret.postgres_password.arn
  sensitive   = true
}

output "microservice_endpoints" {
  description = "Endpoints públicos de los microservicios"
  value = {
    marketplace    = "http://${aws_eip.ec2.public_ip}:8000"
    verificacion   = "http://${aws_eip.ec2.public_ip}:8001"
    cotizacion     = "http://${aws_eip.ec2.public_ip}:8002"
    notificaciones = "http://${aws_eip.ec2.public_ip}:8003"
  }
}

output "pulsar_endpoints" {
  description = "Endpoints de Apache Pulsar"
  value = {
    binary_protocol = "pulsar://${aws_eip.ec2.public_ip}:6650"
    admin_api       = "http://${aws_eip.ec2.public_ip}:8080"
    admin_api_alt   = "http://${aws_eip.ec2.public_ip}:8081"
  }
}

output "ssh_command" {
  description = "Comando sugerido para conectarse por SSH (requiere key pair)"
  value       = var.key_pair_name != "" ? "ssh -i ~/.ssh/${var.key_pair_name}.pem ubuntu@${aws_eip.ec2.public_ip}" : "Usar AWS Systems Manager Session Manager: aws ssm start-session --target ${aws_instance.main.id}"
}
