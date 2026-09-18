# -----------------------------------------------------------------------------
# AMI de Ubuntu 22.04 LTS
# -----------------------------------------------------------------------------
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# -----------------------------------------------------------------------------
# S3 Bucket para archivos de despliegue
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "deploy" {
  bucket = "${local.name_prefix}-deploy-${data.aws_caller_identity.current.account_id}"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-deploy"
  })
}

resource "aws_s3_bucket_versioning" "deploy" {
  bucket = aws_s3_bucket.deploy.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "deploy" {
  bucket = aws_s3_bucket.deploy.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "deploy" {
  bucket = aws_s3_bucket.deploy.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# Empaquetar y subir el proyecto completo a S3
# -----------------------------------------------------------------------------
data "archive_file" "project" {
  type        = "zip"
  output_path = "${path.module}/../hogar-alpes-project.zip"
  source_dir  = "${path.module}/.."

  excludes = [
    ".git/**",
    ".gitignore",
    ".idea/**",
    ".ruff_cache/**",
    "venv/**",
    ".venv/**",
    "terraform/.terraform/**",
    "terraform/.terraform.lock.hcl",
    "terraform/terraform.tfvars",
    "*.zip",
    "*.tfstate",
    "*.tfstate.*",
    ".env",
    "__pycache__/**",
    "*.pyc"
  ]
}

resource "aws_s3_object" "project_zip" {
  bucket = aws_s3_bucket.deploy.id
  key    = "deploy/hogar-alpes-project.zip"
  source = data.archive_file.project.output_path
  etag   = data.archive_file.project.output_md5
}

# -----------------------------------------------------------------------------
# Elastic IP para acceso estable
# -----------------------------------------------------------------------------
resource "aws_eip" "ec2" {
  instance = aws_instance.main.id
  domain   = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-eip"
  })

  depends_on = [aws_internet_gateway.main]
}

# -----------------------------------------------------------------------------
# Instancia EC2 principal
# -----------------------------------------------------------------------------
resource "aws_instance" "main" {
  ami           = var.ec2_ami != "" ? var.ec2_ami : data.aws_ami.ubuntu.id
  instance_type = var.ec2_instance_type
  key_name      = var.key_pair_name != "" ? var.key_pair_name : null

  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  root_block_device {
    volume_size           = var.ec2_root_volume_size
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = templatefile("${path.module}/templates/bootstrap.sh.tpl", {
    s3_bucket               = aws_s3_bucket.deploy.bucket
    docker_compose_file     = var.docker_compose_file
    postgres_user           = local.postgres_user
    postgres_secret_name    = aws_secretsmanager_secret.postgres_password.name
    pulsar_cluster_name     = var.pulsar_cluster_name
    pulsar_volume_size_gb   = var.pulsar_ebs_volume_size
    postgres_volume_size_gb = var.postgres_ebs_volume_size
  })

  user_data_replace_on_change = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ec2"
  })

  depends_on = [
    aws_internet_gateway.main,
    aws_s3_object.project_zip,
    aws_secretsmanager_secret_version.postgres_password
  ]
}

# -----------------------------------------------------------------------------
# Adjuntar volúmenes EBS a la instancia
# -----------------------------------------------------------------------------
resource "aws_volume_attachment" "pulsar" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.pulsar.id
  instance_id = aws_instance.main.id

  stop_instance_before_detaching = true
}

resource "aws_volume_attachment" "postgres" {
  device_name = "/dev/sdg"
  volume_id   = aws_ebs_volume.postgres.id
  instance_id = aws_instance.main.id

  stop_instance_before_detaching = true
}

# -----------------------------------------------------------------------------
# Data source para obtener el ID de cuenta AWS
# -----------------------------------------------------------------------------
data "aws_caller_identity" "current" {}
