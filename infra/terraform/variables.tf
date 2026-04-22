# ──────────────────────────────────────────────────────────────
# Terraform variables · MSPShield Yandex Cloud baseline
# ──────────────────────────────────────────────────────────────
# RU: Все переменные задаются в terraform.tfvars (локально,
# .gitignore). Для прод-окружения — в Yandex Cloud Lockbox или
# через TF_VAR_* переменные окружения.

variable "env" {
  type        = string
  description = "Окружение: dev | staging | prod. Влияет на имена ресурсов и labels."
  default     = "prod"
}

variable "zone" {
  type        = string
  description = "Зона размещения ресурсов Yandex Cloud."
  default     = "ru-central1-a"
}

variable "folder_id" {
  type        = string
  description = "ID folder'а в Yandex Cloud (yc config get folder-id)."
}

variable "ubuntu_image_id" {
  type        = string
  description = "Image ID Ubuntu 22.04 LTS. Найти: `yc compute image list --folder-id standard-images`."
}

variable "ssh_public_key" {
  type        = string
  description = "SSH-pubkey владельца для первичного доступа к VM (user ubuntu)."
}

variable "admin_ssh_sources" {
  type        = list(string)
  description = "Список CIDR'ов, которым разрешён SSH на bastion (например, ['1.2.3.4/32'] — домашний IP)."
  default     = []
}
