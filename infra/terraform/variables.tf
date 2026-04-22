variable "env" {
  type        = string
  description = "dev | staging | prod"
  default     = "prod"
}

variable "zone" {
  type    = string
  default = "ru-central1-a"
}

variable "folder_id" {
  type        = string
  description = "Yandex Cloud folder ID"
}

variable "ubuntu_image_id" {
  type        = string
  description = "Ubuntu 22.04 LTS image id (find via `yc compute image list --folder-id standard-images`)"
}

variable "ssh_public_key" {
  type        = string
  description = "Authorized SSH pubkey for initial access"
}

variable "admin_ssh_sources" {
  type        = list(string)
  description = "CIDRs allowed to SSH into bastion directly"
  default     = []
}
