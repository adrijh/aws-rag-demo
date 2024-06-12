data "aws_iam_policy_document" "this" {
  statement {
    effect = "Allow"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions   = ["es:*"]
    resources = ["arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/${local.app_name}/*"]
  }
}

resource "aws_iam_service_linked_role" "this" {
  aws_service_name = "opensearchservice.amazonaws.com"
}

resource "time_sleep" "await_role_propagation" {
  depends_on = [aws_iam_service_linked_role.this]

  create_duration = "10s"
}

resource "aws_opensearch_domain" "this" {
  depends_on = [time_sleep.await_role_propagation]

  domain_name    = local.app_name
  engine_version = "OpenSearch_2.11"

  cluster_config {
    dedicated_master_enabled = false
    instance_count           = 1
    instance_type            = "t3.small.search"
    zone_awareness_enabled   = false
  }

  ebs_options {
    ebs_enabled = true
    iops        = 3000
    throughput  = 125
    volume_size = 20
    volume_type = "gp3"
  }

  vpc_options {
    subnet_ids = [
      data.aws_subnets.private.ids[0],
    ]

    security_group_ids = [aws_security_group.opensearch.id]
  }

  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
  }

  access_policies = data.aws_iam_policy_document.this.json
}
