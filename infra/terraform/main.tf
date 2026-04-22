# ──────────────────────────────────────────────────────────────
# MSPShield · Yandex Cloud baseline infrastructure (landing + bastion)
# ──────────────────────────────────────────────────────────────
# Deploys:
#  • mspshield-landing VM (backend + frontend + mongo + nginx)
#  • mspshield-bastion VM (WireGuard concentrator for all tenants)
#  • Object Storage bucket for restic backups
#  • IAM service accounts with minimum-privilege policies
#
# Not included here (kept in separate TF stacks):
#  • Per-client tenant VMs (var-driven)
#  • SIEM (Wazuh) stack
#  • Vaultwarden VM
# ──────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5"
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.100"
    }
  }
  backend "s3" {
    endpoint = "storage.yandexcloud.net"
    bucket   = "mspshield-tfstate"
    key      = "landing/terraform.tfstate"
    region   = "ru-central1"
    skip_region_validation      = true
    skip_credentials_validation = true
  }
}

provider "yandex" {
  zone = var.zone
}

# ── Network ───────────────────────────────────────────────────
resource "yandex_vpc_network" "core" {
  name = "mspshield-core"
}

resource "yandex_vpc_subnet" "core_a" {
  name           = "mspshield-core-a"
  zone           = var.zone
  network_id     = yandex_vpc_network.core.id
  v4_cidr_blocks = ["10.10.0.0/24"]
}

# ── Landing VM ────────────────────────────────────────────────
resource "yandex_compute_instance" "landing" {
  name        = "mspshield-landing"
  platform_id = "standard-v3"
  zone        = var.zone

  resources {
    cores         = 2
    memory        = 4
    core_fraction = 100
  }

  boot_disk {
    initialize_params {
      image_id = var.ubuntu_image_id
      size     = 40
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.core_a.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.landing.id]
  }

  metadata = {
    ssh-keys  = "ubuntu:${var.ssh_public_key}"
    user-data = file("${path.module}/cloud-init/landing.yaml")
  }

  scheduling_policy {
    preemptible = false
  }

  labels = {
    role = "landing"
    env  = var.env
  }
}

# ── Bastion VM ────────────────────────────────────────────────
resource "yandex_compute_instance" "bastion" {
  name        = "mspshield-bastion"
  platform_id = "standard-v3"
  zone        = var.zone

  resources {
    cores         = 2
    memory        = 2
    core_fraction = 50
  }

  boot_disk {
    initialize_params {
      image_id = var.ubuntu_image_id
      size     = 30
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.core_a.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.bastion.id]
  }

  metadata = {
    ssh-keys  = "ubuntu:${var.ssh_public_key}"
    user-data = file("${path.module}/cloud-init/bastion.yaml")
  }

  labels = {
    role = "bastion"
    env  = var.env
  }
}

# ── Security groups ───────────────────────────────────────────
resource "yandex_vpc_security_group" "landing" {
  name       = "mspshield-landing-sg"
  network_id = yandex_vpc_network.core.id

  ingress {
    protocol       = "TCP"
    description    = "HTTP"
    port           = 80
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    protocol       = "TCP"
    description    = "HTTPS"
    port           = 443
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    protocol       = "TCP"
    description    = "SSH — only from bastion"
    port           = 22
    v4_cidr_blocks = ["10.10.0.0/24"]
  }
  egress {
    protocol       = "ANY"
    description    = "all outbound"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "yandex_vpc_security_group" "bastion" {
  name       = "mspshield-bastion-sg"
  network_id = yandex_vpc_network.core.id

  ingress {
    protocol       = "UDP"
    description    = "WireGuard"
    port           = 51820
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    protocol       = "TCP"
    description    = "SSH — only admin IPs"
    port           = 22
    v4_cidr_blocks = var.admin_ssh_sources
  }
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── Object storage (backups) ──────────────────────────────────
resource "yandex_iam_service_account" "restic" {
  name = "mspshield-restic-backup"
}

resource "yandex_resourcemanager_folder_iam_binding" "restic_editor" {
  folder_id = var.folder_id
  role      = "storage.editor"
  members   = ["serviceAccount:${yandex_iam_service_account.restic.id}"]
}

resource "yandex_iam_service_account_static_access_key" "restic" {
  service_account_id = yandex_iam_service_account.restic.id
  description        = "Restic S3 key"
}

resource "yandex_storage_bucket" "backups" {
  bucket     = "mspshield-backups-${var.env}"
  access_key = yandex_iam_service_account_static_access_key.restic.access_key
  secret_key = yandex_iam_service_account_static_access_key.restic.secret_key

  versioning {
    enabled = true
  }

  lifecycle_rule {
    id      = "old-versions-cleanup"
    enabled = true
    noncurrent_version_expiration {
      days = 90
    }
  }
}

# ── Outputs ───────────────────────────────────────────────────
output "landing_public_ip" {
  value = yandex_compute_instance.landing.network_interface[0].nat_ip_address
}

output "bastion_public_ip" {
  value = yandex_compute_instance.bastion.network_interface[0].nat_ip_address
}

output "backup_bucket" {
  value = yandex_storage_bucket.backups.bucket
}
