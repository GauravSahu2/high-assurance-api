# Terraform snippet to enforce IMDSv2 and block metadata access for ECS tasks
resource "aws_security_group" "api_task_sg" {
  name        = "api-task-sg"
  description = "Security Group for API Tasks"
  vpc_id      = var.vpc_id

  # Allow all HTTPS outbound (for Secrets Manager, external APIs)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Explicitly DENY outbound to 169.254.169.254 (Network ACLs usually needed for explicit deny, 
  # but omitting it from specific allowed CIDRs blocks it. To be strictly compliant with the Black Hat standard:)
}

# Require IMDSv2 at the EC2/Node level (Blocks SSRF natively by requiring a PUT request for a token first)
resource "aws_launch_template" "api_nodes" {
  name = "api-node-template"
  # ... other configs ...
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # Forces IMDSv2
    http_put_response_hop_limit = 1          # Prevents containers from hopping to the host's metadata
  }
}
