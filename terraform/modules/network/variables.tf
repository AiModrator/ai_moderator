

variable "context" {
  description = "Le contexte des resources"
  type = object(
    {
      name = string
      env = string
      cluster_name = string
    }
  )
}


variable "availability_zones" {
  description = "List of availability zones , il faut  au moins 2 zones"
  type = list(string)
  validation{
    condition = length(var.availability_zones) > 1
    error_message = "Il faut au moins deux avaibility zones "
  }  
}
