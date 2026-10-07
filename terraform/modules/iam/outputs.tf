output "aws_eks_role_arn" {
  description = "exportation des role du cluster"
  value = aws_iam_role.eks_cluster_role.arn
}

output "aws_nodes_role_arn" {
  description = "exportation des role du noeuds"
  value = aws_iam_role.eks_node_role.arn
}



output "aws_karpenter_role" {
  description = "role du  karpenter"  
  value = aws_iam_role.karpenter_role.arn
}


output "aws_ebs_csi_role" {
  description = "role du  ebs csi"  
  value = aws_iam_role.ebs_csi.arn
}


output "aws_lb_role" {
  description = "role du lb controller"  
  value = aws_iam_role.lb_controller.arn
}   