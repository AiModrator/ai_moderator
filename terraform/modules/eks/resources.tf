

resource "aws_eks_cluster" "eks" {
  name     = var.context.cluster_name
  role_arn = var.context.eks_role_arn

  # version non fixe : AWS utilise la version par defaut de la region.
  # Pour la prod, il est recommande de la piner (ex: version = "1.34")
  # des que la version cible est validee.

  access_config {
    authentication_mode = "API"
  }


  vpc_config {

    subnet_ids = var.context.public_subnet_ids

    security_group_ids = var.context.controle_plane_security_group_ids

    endpoint_private_access = false
    endpoint_public_access  = true

    public_access_cidrs = ["0.0.0.0/0"]

    control_plane_egress_mode = "AWS_MANAGED"
  }

  kubernetes_network_config {
    ip_family         = "ipv4"
    service_ipv4_cidr = "172.20.0.0/16"
  }

  # NOTE : pas de compute_config / storage_config / elastic_load_balancing ici :
  #       ce sont des options EKS Auto Mode. Ce cluster est un cluster classique
  #       avec des managed node groups (voir rapport d'erreurs logiques).

  bootstrap_self_managed_addons = true

  tags = {
    name = "eks_cluster_${var.context.name}"
    env  = var.context.env
  }
}


# ======================================== Addons ========================================




resource "aws_eks_addon" "pod_identity_addons" {
  cluster_name = aws_eks_cluster.eks.name
  addon_name   = "eks-pod-identity-agent"
}






# ======================================== Karpenter ========================================




resource "aws_eks_node_group" "karpenter_controller" {

  cluster_name    = aws_eks_cluster.eks.name
  node_group_name = "karpenter_controller_${var.context.env}"

  node_role_arn = var.context.node_roles_arn

  subnet_ids = [var.context.karpenter_subnet_id]

  scaling_config {
    desired_size = 1
    min_size     = 1
    max_size     = 1
  }

  ami_type      = "AL2023_x86_64_STANDARD"
  capacity_type = "ON_DEMAND"

  # 1. Label pour identifier le noeud
  labels = {
    "karpenter.sh/controller" = "true"
  }

  # 2. Taint pour repousser les autres pods applicatifs (recommande)
  taint {
    key    = "karpenter.sh/controller"
    value  = "true"
    effect = "NO_SCHEDULE"
  }


  update_config {
    max_unavailable = 1
  }

  launch_template {
    name    = aws_launch_template.worker_launch_template.name
    version = aws_launch_template.worker_launch_template.latest_version
  }

  lifecycle {
    ignore_changes = [
      scaling_config[0].desired_size
    ]
  }


}

resource "aws_launch_template" "worker_launch_template" {
  name                   = "karpenter_worker_${var.context.env}"
  update_default_version = true

  # Pas d'image_id : EKS choisit automatiquement l'AMI correspondant a la
  # version du cluster (AMI figee sur 1.30 -> noeuds incapables de joindre un
  # cluster plus recent).
  instance_type = "t3.small"

  # Les security groups des noeuds (decouverte Karpenter) passent ici.
  # aws_eks_node_group ne possede pas d'argument "node_security_group_ids".
  vpc_security_group_ids = var.context.karpenter_security_group_id

  tag_specifications {
    resource_type = "instance"
    tags = {
      name                       = "karpenter_controller_${var.context.env}"
      env                        = var.context.env
      "karpenter.sh/discovery"   = var.context.cluster_name
    }
  }
}






resource "kubernetes_service_account_v1" "karpenter" {
  metadata {
    name      = "karpenter"
    namespace = "kube-system"

    # NOTE : Aucune annotation IAM n'est requise ici !
    # C'est l'association Pod Identity ci-dessous qui fait le lien en tache de fond.
    labels = {
      "app.kubernetes.io/name" = "karpenter"
    }
  }
}




resource "aws_eks_pod_identity_association" "app_assoc" {
  cluster_name    = aws_eks_cluster.eks.name
  namespace       = "kube-system"
  service_account = kubernetes_service_account_v1.karpenter.metadata[0].name
  role_arn        = var.context.karpenter_role_arn

  # S'assure que l'agent est bien installe avant l'association
  depends_on = [aws_eks_addon.pod_identity_addons]
}




resource "helm_release" "karpenter" {
  name             = "karpenter"
  namespace        = "kube-system"
  create_namespace = false

  repository = "oci://public.ecr.aws/karpenter"
  chart      = "karpenter"
  version    = "1.12.1"

  values = [
    yamlencode({
      settings = {
        clusterName = aws_eks_cluster.eks.name
      }

      # Le ServiceAccount est gere par Terraform (pod identity association)
      serviceAccount = {
        create = false
        name   = "karpenter"
      }

      # Le seul noeud du cluster porte ce label + ce taint
      nodeSelector = {
        "karpenter.sh/controller" = "true"
      }

      tolerations = [
        {
          key      = "karpenter.sh/controller"
          operator = "Exists"
          effect   = "NoSchedule"
        }
      ]
    })
  ]

  # Le ServiceAccount + l'association pod identity + le noeud dedie
  # doivent exister avant le chart
  depends_on = [
    aws_eks_node_group.karpenter_controller,
    aws_eks_pod_identity_association.app_assoc
  ]
}





# ======================================== CSI  driver ========================================


resource "helm_release" "aws_ebs_csi" {
  name             = "aws-ebs-csi-driver"
  namespace        = "kube-system"
  create_namespace = false

  repository = "https://kubernetes-sigs.github.io/aws-ebs-csi-driver"
  chart      = "aws-ebs-csi-driver"
  version    = "2.39.0"

  values = [
    yamlencode({
      controller = {
        serviceAccount = {
          create = false
          name   = "ebs-csi-controller-sa"
        }

        # Les controleurs doivent tomber sur le noeud dedie (label + taint)
        nodeSelector = {
          "karpenter.sh/controller" = "true"
        }

        tolerations = [
          {
            key      = "karpenter.sh/controller"
            operator = "Exists"
            effect   = "NoSchedule"
          }
        ]
      }
      # Le DaemonSet node (tolerateAllTaints: true par defaut) s'occupe du reste
    })
  ]

  depends_on = [aws_eks_pod_identity_association.ebs_csi]
}




resource "aws_eks_pod_identity_association" "ebs_csi" {
  cluster_name    = aws_eks_cluster.eks.name
  namespace       = "kube-system"
  service_account = kubernetes_service_account_v1.ebs_csi.metadata[0].name
  role_arn        = var.context.csi_role_arn

  depends_on = [aws_eks_addon.pod_identity_addons]
}




resource "kubernetes_service_account_v1" "ebs_csi" {
  metadata {
    name      = "ebs-csi-controller-sa"
    namespace = "kube-system"
    labels = {
      "app.kubernetes.io/component" = "controller"
      "app.kubernetes.io/name"      = "aws-ebs-csi-driver"
    }
  }
}





# ======================================== Load balancer ========================================



resource "helm_release" "aws_lbc" {
  name             = "aws-load-balancer-controller"
  namespace        = "kube-system"
  create_namespace = false

  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = "1.14.0"

  values = [
    yamlencode({
      clusterName = aws_eks_cluster.eks.name

      serviceAccount = {
        create = false
        name   = "aws-load-balancer-controller"
      }

      nodeSelector = {
        "karpenter.sh/controller" = "true"
      }

      tolerations = [
        {
          key      = "karpenter.sh/controller"
          operator = "Exists"
          effect   = "NoSchedule"
        }
      ]
    })
  ]

  depends_on = [aws_eks_pod_identity_association.lb_controller]
}



resource "aws_eks_pod_identity_association" "lb_controller" {
  cluster_name    = aws_eks_cluster.eks.name
  namespace       = "kube-system"
  service_account = kubernetes_service_account_v1.lb_controller.metadata[0].name
  role_arn        = var.context.load_balancer_controller_role_arn

  depends_on = [aws_eks_addon.pod_identity_addons]
}




resource "kubernetes_service_account_v1" "lb_controller" {
  metadata {
    name      = "aws-load-balancer-controller"
    namespace = "kube-system"
    labels = {
      "app.kubernetes.io/component" = "controller"
      "app.kubernetes.io/name"      = "aws-load-balancer-controller"
    }
  }
}
