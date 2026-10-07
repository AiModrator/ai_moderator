



variable "context" {
  description = "Le contexte des resources"
  type = object(
    {
      env = string
      name = string
    }
  )
}