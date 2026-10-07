# =============================================================================
#  Remote state : S3 (+ verrou DynamoDB)
# -----------------------------------------------------------------------------
#  Le state n'est JAMAIS commite dans git (voir .gitignore).
#
#  Le bucket et la table doivent exister AVANT le premier `terraform apply`
#  (un backend ne peut pas etre provisionne par la configuration qui l'utilise).
#  Commandes a executer une seule fois :
#
#    aws s3api create-bucket \
#      --bucket ai-moderator-terraform-state \
#      --region us-east-1
#
#    aws s3api put-bucket-versioning \
#      --bucket ai-moderator-terraform-state \
#      --versioning-configuration Status=Enabled
#
#    aws s3api put-bucket-encryption \
#      --bucket ai-moderator-terraform-state \
#      --server-side-encryption-configuration \
#      '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}'
#
#    aws dynamodb create-table \
#      --table-name ai-moderator-terraform-locks \
#      --attribute-definitions AttributeName=LockID,AttributeType=S \
#      --key-schema AttributeName=LockID,KeyType=HASH \
#      --billing-mode PAY_PER_REQUEST \
#      --region us-east-1
#
#  Puis : terraform init   (premiere fois : terraform init -migrate-state)
# =============================================================================

terraform {
  backend "s3" {
    bucket         = "ai-moderator-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "ai-moderator-terraform-locks"
    encrypt        = true
  }
}
