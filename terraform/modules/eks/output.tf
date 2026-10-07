output "cluster_name" {
  description = "Nom du cluster EKS"
  value       = aws_eks_cluster.eks.name
}

output "cluster_endpoint" {
  description = "Endpoint de l'API server EKS"
  value       = aws_eks_cluster.eks.endpoint
}

output "cluster_certificate_authority_data" {
  description = "Certificat CA du cluster (base64)"
  value       = aws_eks_cluster.eks.certificate_authority[0].data
}

output "cluster_oidc_issuer_url" {
  description = "URL de l'OIDC issuer du cluster"
  value       = aws_eks_cluster.eks.identity[0].oidc[0].issuer
}
