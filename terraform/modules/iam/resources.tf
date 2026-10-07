# ================================= eks cluster role =========================================

resource "aws_iam_role" "eks_cluster_role" {

  name = "eks_cluster_role_${var.context.env}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    name = "eks_cluster_role_${var.context.name}"
    env  = var.context.env
  }
}


resource "aws_iam_role_policy_attachment" "eks_policy_attachment" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}


# ============================ eks nodes roles ==============================================================================

resource "aws_iam_role" "eks_node_role" {

  name = "node_role_cluster_${var.context.env}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    name = "node_role_cluster_${var.context.name}"
    env  = var.context.env
  }
}


resource "aws_iam_role_policy_attachment" "node_eks_policy_attachment" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}


# Sans ces deux policies les noeuds se joignent au cluster mais aucun pod ne peut
# obtenir d'IP (VPC CNI) ni tirer d'image (ECR).
resource "aws_iam_role_policy_attachment" "node_cni_policy_attachment" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}


resource "aws_iam_role_policy_attachment" "node_ecr_policy_attachment" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}


# ============================ karpenter role ========================================================================


resource "aws_iam_role" "karpenter_role" {

  # NB : ne doit pas porter le meme nom que eks_cluster_role (erreur AWS "entity already exists")
  name = "karpenter_role_${var.context.env}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["sts:AssumeRole", "sts:TagSession"]
        Principal = {
          type        = "Service"
          identifiers = ["pods.eks.amazonaws.com"]
        }
      }
    ]
  })

  tags = {
    name = "karpenter_role_${var.context.name}"
    env  = var.context.env
  }
}

# 1. Creer votre propre politique KarpenterControllerPolicy
resource "aws_iam_policy" "karpenter_controller" {
  name        = "KarpenterControllerPolicy-${var.context.env}"
  path        = "/"
  description = "Permissions requises pour le controleur Karpenter"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateFleet",
          "ec2:CreateLaunchTemplate",
          "ec2:CreateTags",
          "ec2:DeleteLaunchTemplate",
          "ec2:DescribeImages",
          "ec2:DescribeInstanceTypeOfferings",
          "ec2:DescribeInstanceTypes",
          "ec2:DescribeInstances",
          "ec2:DescribeLaunchTemplates",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeSpotPriceHistory",
          "ec2:DescribeSubnets",
          "ec2:RunInstances",
          "ec2:TerminateInstances",
          "pricing:GetProducts",
          "eks:DescribeCluster"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.eks_node_role.arn] # Le role IAM utilise par les noeuds EC2
      }
    ]
  })
}


resource "aws_iam_role_policy_attachment" "karpenter_policy_attachment" {
  role       = aws_iam_role.karpenter_role.name
  policy_arn = aws_iam_policy.karpenter_controller.arn
}



# ======================================== ebs csi role ========================================




resource "aws_iam_role" "ebs_csi" {
  name = "eks-ebs-csi-role-${var.context.env}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action = [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }]
  })

  tags = {
    env = var.context.env
  }
}


resource "aws_iam_role_policy_attachment" "ebs_csi" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
  role       = aws_iam_role.ebs_csi.name
}


# ================================================= lb controller role ======================================================


resource "aws_iam_role" "lb_controller" {
  name = "eks-lb-controller-role-${var.context.env}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action = ["sts:AssumeRole", "sts:TagSession"]
    }]
  })

  tags = {
    env = var.context.env
  }
}


resource "aws_iam_role_policy_attachment" "lb_controller" {
  policy_arn = aws_iam_policy.aws_load_balancer_controller.arn
  role       = aws_iam_role.lb_controller.name
}




# 2. Politique IAM officielle du Load Balancer Controller, stockee en local
#    (pas de dependance reseau au moment du plan/apply).
resource "aws_iam_policy" "aws_load_balancer_controller" {
  name        = "AWSLoadBalancerControllerIAMPolicy-${var.context.env}"
  path        = "/"
  description = "Politique IAM pour AWS Load Balancer Controller gere par EKS"
  policy      = file("${path.module}/iam_policy_lb.json")

  tags = {
    env = var.context.env
  }
}
