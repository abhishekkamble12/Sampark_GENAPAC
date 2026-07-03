variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region for resource deployment"
  type        = string
  default     = "asia-south1"
}

variable "artifact_registry" {
  description = "Artifact Registry host (e.g. asia-south1-docker.pkg.dev/my-project/my-repo)"
  type        = string
}

variable "vpc_connector" {
  description = "Fully-qualified VPC Serverless Access connector name for private VPC access"
  type        = string
  default     = ""
}

variable "rag_corpus_id" {
  description = "Vertex AI RAG Engine corpus ID for policy document retrieval"
  type        = string
  default     = ""
}
