# CAL FIRE Wildfire Intelligence Platform - Storage Infrastructure
# Terraform Configuration for Hybrid Cloud Storage Architecture
# Version: 1.0.0

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "wildfire-terraform-state"
    key            = "storage/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "wildfire-terraform-locks"
  }
}

# Provider Configurations
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "CAL-FIRE-Wildfire-Intelligence"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Challenge   = "Challenge2-DataStorage"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Local Variables
locals {
  common_tags = {
    Project     = "CAL-FIRE-Wildfire-Intelligence"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Challenge   = "Challenge2-DataStorage"
  }

  data_sources = [
    "firms_modis_terra",
    "firms_modis_aqua",
    "firms_viirs_snpp",
    "firms_viirs_noaa20",
    "firms_viirs_noaa21",
    "firesat_detections",
    "firesat_perimeters",
    "landsat_nrt",
    "sentinel3_slstr",
    "noaa_gfs_forecast",
    "airnow_observations"
  ]
}
