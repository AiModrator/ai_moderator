locals {
  env = "prod"
  name = "ai_moderator"

  # Nom du cluster EKS : obligatoire (nom de ressource + tags karpenter / kubernetes.io/cluster/<name>)
  cluster_name = "${local.name}-${local.env}"

  availability_zones = ["us-east-1a", "us-east-1b"]
}


module "network" {
  source = "../../modules/network"

  context = {
    env          = local.env
    name         = local.name
    cluster_name = local.cluster_name
  }

  availability_zones = local.availability_zones
}


module "iam_role" {
  source = "../../modules/iam"

  context = {
    env  = local.env
    name = local.name
  }
}


module "eks" {
  source = "../../modules/eks"

  context = {
    env  = local.env
    name = local.name

    cluster_name = local.cluster_name

    eks_role_arn                     = module.iam_role.aws_eks_role_arn
    controle_plane_security_group_ids = [module.network.aws_eks_security_group]
    public_subnet_ids                 = module.network.aws_public_subnets

    karpenter_role_arn           = module.iam_role.aws_karpenter_role
    karpenter_security_group_id  = [module.network.aws_node_security_group]
    karpenter_subnet_id          = module.network.aws_private_subnets[0]

    node_roles_arn       = module.iam_role.aws_nodes_role_arn
    node_security_groups = [module.network.aws_node_security_group]
    private_subnet_ids   = module.network.aws_private_subnets

    csi_role_arn = module.iam_role.aws_ebs_csi_role

    load_balancer_controller_role_arn = module.iam_role.aws_lb_role
  }
}
