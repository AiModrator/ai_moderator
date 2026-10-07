

variable "context" {
  description = "Le contexte des resources"
  type = object(
    {
      env  = string
      name = string

      eks_role_arn                      = string
      controle_plane_security_group_ids = list(string)
      public_subnet_ids                 = list(string)


      karpenter_role_arn          = string
      karpenter_security_group_id = list(string)
      karpenter_subnet_id         = string


      private_subnet_ids   = list(string)
      node_security_groups = list(string)
      node_roles_arn       = string


      csi_role_arn = string

      load_balancer_controller_role_arn = string

      cluster_name = string
    }
  )
}
