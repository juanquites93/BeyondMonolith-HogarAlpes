# -----------------------------------------------------------------------------
# Rol IAM para la instancia EC2
# -----------------------------------------------------------------------------
resource "aws_iam_role" "ec2" {
  name = "${local.name_prefix}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Política para gestión de volúmenes EBS
resource "aws_iam_policy" "ebs_management" {
  name        = "${local.name_prefix}-ebs-management"
  description = "Permite a la EC2 describir, adjuntar y desvincular volúmenes EBS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeVolumes",
          "ec2:DescribeVolumeAttribute",
          "ec2:DescribeVolumeStatus",
          "ec2:DescribeInstances",
          "ec2:AttachVolume",
          "ec2:DetachVolume"
        ]
        Resource = "*"
      }
    ]
  })
}

# Política para acceso a Secrets Manager (credenciales generadas)
resource "aws_iam_policy" "secrets_read" {
  name        = "${local.name_prefix}-secrets-read"
  description = "Permite leer secrets de AWS Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.postgres_password.arn
      }
    ]
  })
}

# Adjuntar políticas administradas y personalizadas al rol
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ebs" {
  role       = aws_iam_role.ec2.name
  policy_arn = aws_iam_policy.ebs_management.arn
}

resource "aws_iam_role_policy_attachment" "secrets" {
  role       = aws_iam_role.ec2.name
  policy_arn = aws_iam_policy.secrets_read.arn
}

# Instance profile para asociar el rol a la EC2
resource "aws_iam_instance_profile" "ec2" {
  name = "${local.name_prefix}-ec2-profile"
  role = aws_iam_role.ec2.name

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# Secrets Manager - contraseña de PostgreSQL
# -----------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "postgres_password" {
  name                    = "${local.name_prefix}-postgres-password"
  description             = "Contraseña del usuario administrador de PostgreSQL"
  recovery_window_in_days = 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "postgres_password" {
  secret_id     = aws_secretsmanager_secret.postgres_password.id
  secret_string = local.postgres_password
}
