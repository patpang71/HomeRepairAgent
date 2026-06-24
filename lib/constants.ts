export const AWS_REGION = 'us-east-1';

export const PROJECT_NAME = 'HomeRepairAgent';

export const RAG_DB_NAME = 'HomeRepairRAGDB';

// Aurora cluster identifier — sets the physical resource name in AWS (no random suffix)
export const RAG_DB_CLUSTER_ID = 'home-repair-rag-db';

// S3 bucket for source PDF documents
export const PDF_SOURCE_BUCKET_NAME = 'home-repair-agent-pdfs';

// Bedrock Knowledge Base name
export const KNOWLEDGE_BASE_NAME = 'HomeRepairKnowledgeBase';

// Amazon Nova model ID for the Bedrock agent
export const BEDROCK_AGENT_MODEL_ID = 'amazon.nova-pro-v1:0';

// Bedrock embedding model for pgvector ingestion
export const BEDROCK_EMBEDDING_MODEL_ID = 'amazon.titan-embed-text-v2:0';

// Vector dimensions for Titan Embeddings v2
export const EMBEDDING_DIMENSIONS = 1024;
