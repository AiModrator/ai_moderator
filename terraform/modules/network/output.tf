

output "aws_node_security_group" {
  description = "exportation des security group du noeuds"
  value       = aws_security_group.worker_security_group.id
}


output "aws_eks_security_group" {
  description = "exportation des security group du cluster"
  value       = aws_security_group.eks_security_group.id
}



output "aws_private_subnets" {
  description = "exportation des private subnet pour (nodes , karpenter et load balancer controller)"
  value       = [for k, s in aws_subnet.private_subnets : s.id]
}


output "aws_public_subnets" {
  description = "exportation des public subnet pour (eks ENI )"
  value       = [for k, s in aws_subnet.public_subnets : s.id]
}
