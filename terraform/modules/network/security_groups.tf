


resource "aws_security_group" "eks_security_group" {
  name = "eks_security_group_${var.context.name}"

  description = "Le group de securite pour le controle plane "

  vpc_id = aws_vpc.main_vpc.id 

  tags = {
    name = "security_group_eks_${var.context.name}"
    env = "${var.context.env}"
  }

  
}





resource "aws_vpc_security_group_ingress_rule" "inbound_https" {
  security_group_id = aws_security_group.eks_security_group.id
  to_port = 443
  from_port = 443
  ip_protocol = "tcp"
  cidr_ipv4 = "0.0.0.0/0"

}

resource "aws_vpc_security_group_egress_rule" "outbound_kubelet" {
  security_group_id = aws_security_group.eks_security_group.id
  from_port         = 1024
  to_port           = 65535
  ip_protocol       = "tcp"
  referenced_security_group_id = aws_security_group.worker_security_group.id
}







# pour les noeuds  

resource "aws_security_group" "worker_security_group" {
  name = "worker_security_group_${var.context.name}"

  description = "Le group de securite pour les noeuds   "

  vpc_id = aws_vpc.main_vpc.id 

  tags = {
    name = "worker_security_group_${var.context.name}"
    env = "${var.context.env}"
    "karpenter.sh/discovery" = var.context.cluster_name

  } 
}



resource "aws_vpc_security_group_ingress_rule" "worker_control_ingress" {
  security_group_id = aws_security_group.worker_security_group.id
  to_port = 65535
  from_port =  1024
  ip_protocol = "tcp"
  referenced_security_group_id =  aws_security_group.eks_security_group.id
} 


resource "aws_vpc_security_group_ingress_rule" "worker_control_ingress_https" {
  security_group_id = aws_security_group.worker_security_group.id
  to_port = 443
  from_port = 443
  ip_protocol = "tcp"
  referenced_security_group_id =  aws_security_group.eks_security_group.id
} 



resource "aws_vpc_security_group_ingress_rule" "worker_self_connection" {
  security_group_id = aws_security_group.worker_security_group.id
  ip_protocol = "-1"
  referenced_security_group_id =  aws_security_group.worker_security_group.id
} 


resource "aws_vpc_security_group_egress_rule" "worker_control_egress" {
  security_group_id = aws_security_group.worker_security_group.id
  to_port = 443
  from_port = 443
  ip_protocol = "tcp"
  referenced_security_group_id =  aws_security_group.eks_security_group.id
} 


resource "aws_vpc_security_group_egress_rule" "internet_worker" {
  security_group_id = aws_security_group.worker_security_group.id
  ip_protocol = "-1"
  cidr_ipv4 = "0.0.0.0/0"
} 
