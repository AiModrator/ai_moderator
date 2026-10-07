

locals {
  cidr_block            = "10.0.0.0/16"
  availability_zones_number = length(var.availability_zones)

  # for_each exige une map : on indexe les subnets par position (0..n-1)
  public_subnets = {
    for i in range(local.availability_zones_number) : tostring(i) => cidrsubnet(local.cidr_block, 8, i)
  }

  private_subnets = {
    for i in range(local.availability_zones_number) : tostring(i) => cidrsubnet(local.cidr_block, 8, i + local.availability_zones_number)
  }
}


resource "aws_vpc" "main_vpc" {
  cidr_block = local.cidr_block

  tags = {
    name = "vpc_moderation_${var.context.env}"
    env  = var.context.env
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main_vpc.id

  tags = {
    name = "igw_${var.context.env}"
    env  = var.context.env
  }
}


# ======================== publics subnets   ===============================================




resource "aws_subnet" "public_subnets" {
  vpc_id            = aws_vpc.main_vpc.id
  for_each          = local.public_subnets
  cidr_block        = each.value
  availability_zone = var.availability_zones[each.key]

  tags = {
    name = "public_subnet_${each.key}_${var.context.name}"
    env  = var.context.env

    "kubernetes.io/cluster/${var.context.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                           = "1"
  }
}


resource "aws_route_table" "public_table" {

  vpc_id = aws_vpc.main_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    name = "public_table_${var.context.name}"
    env  = var.context.env
  }
}

resource "aws_route_table_association" "public_table_subnet_associations" {

  for_each       = aws_subnet.public_subnets
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public_table.id
}


# ======================== privates subnets   ===============================================



·
resource "aws_route_table" "private_table" {
  vpc_id = aws_vpc.main_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.private_nat.id
  }

  tags = {
    env = var.context.env
  }
}

resource "aws_route_table_association" "private_table_subnet_associations" {
  for_each       = aws_subnet.private_subnets
  route_table_id = aws_route_table.private_table.id
  subnet_id      = each.value.id
}


resource "aws_eip" "eip_nat" {
  domain = "vpc"
  depends_on = [aws_internet_gateway.igw]

  tags = {
    name = "eip_${var.context.name}"
    env  = var.context.env
  }
}

resource "aws_nat_gateway" "private_nat" {

  allocation_id = aws_eip.eip_nat.id

  subnet_id = aws_subnet.public_subnets[0].id

  depends_on = [aws_internet_gateway.igw]

  tags = {
    env  = var.context.env
    name = "nat_${var.context.name}"
  }
}
