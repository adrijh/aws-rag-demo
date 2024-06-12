resource "aws_ecr_repository" "this" {
  name = local.app_name
}

resource "null_resource" "build_image" {

  depends_on = [
    aws_ecr_repository.this
  ]

  triggers = {
    always_run = "${timestamp()}"
  }

  provisioner "local-exec" {
    command = (templatefile("${path.module}/build_image.tpl", {
      aws_account_id = data.aws_caller_identity.current.account_id,
      region         = data.aws_region.current.name,
      repository_url = aws_ecr_repository.this.repository_url,
      image_tag      = "latest",
      source         = "${local.root_path}/src/"
      }
    ))
  }
}

resource "aws_ecs_cluster" "this" {
  name = local.app_name
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecs_task_execution_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}
resource "aws_iam_role" "ecs_task_role" {
  name = "ecs_task_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "opensearch" {
  name        = "opensearch_access_policy"
  description = "Policy to allow access to OpenSearch"
  policy      = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "es:*",
        ],
        Resource = "${aws_opensearch_domain.this.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_opensearch_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.opensearch.arn
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${local.app_name}"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "this" {
  depends_on = [null_resource.build_image]

  family = local.app_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "2048"

  task_role_arn = aws_iam_role.ecs_task_role.arn
  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([{
    name  = local.app_name
    image = "${aws_ecr_repository.this.repository_url}:latest"
    essential = true
    portMappings = [{
      containerPort = 8501
      hostPort      = 8501
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.this.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }
    environment = [
      {
        name  = "AWS_REGION"
        value = data.aws_region.current.name
      },
      {
        name  = "OPENSEARCH_ENDPOINT"
        value = "https://${aws_opensearch_domain.this.endpoint}:443"
      },
      {
        name  = "OPENSEARCH_INDEX_NAME"
        value = local.app_name
      },
      {
        name  = "CLOUD_PROVIDER"
        value = "aws"
      }
    ]
  }])
}

resource "aws_security_group" "ecs_sg" {
  name        = "ecs-sg"
  description = "Allow HTTP inbound traffic"
  vpc_id      = data.aws_vpc.this.id

  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_service" "this" {
  name            = local.app_name
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = data.aws_subnets.private.ids
    security_groups = [aws_security_group.ecs_sg.id, aws_security_group.opensearch_user.id]
  }

  load_balancer {
    container_port = 8501
    container_name = jsondecode(aws_ecs_task_definition.this.container_definitions)[0].name
    target_group_arn = aws_lb_target_group.this.arn
  }
}
