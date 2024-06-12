resource "aws_security_group" "opensearch" {
  name   = "${local.app_name}-opensearch"
  vpc_id = data.aws_vpc.this.id
}

resource "aws_security_group_rule" "opensearch_ingress" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.opensearch_user.id
  security_group_id        = aws_security_group.opensearch.id
}

resource "aws_security_group_rule" "all_egress" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.opensearch.id
}

resource "aws_security_group" "opensearch_user" {
  name   = "${local.app_name}-user"
  vpc_id = data.aws_vpc.this.id
}

resource "aws_security_group_rule" "opensearch_egress" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.opensearch.id
  security_group_id        = aws_security_group.opensearch_user.id
}
