provider "aws" {}

locals {
  root_path = abspath("${path.root}/../../")
  prefix   = ""
  app_name = "rag-demo"
  vpc_id = "vpc-0439461c668168b29"
}

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

data "aws_vpc" "this" {
  id = local.vpc_id
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.this.id]
  }

  tags = {
    Name = "*public*"
  }
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.this.id]
  }

  tags = {
    Name = "*private*"
  }
}

