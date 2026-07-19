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

// Knowledge base retrieval — max chunks to pull back per query, and the minimum
// relevance score (0-1) a chunk needs to count as a "found" answer. Below this
// threshold the agent falls back to Tavily web search.
export const KB_RETRIEVAL_MAX_RESULTS = 5;
export const KB_RETRIEVAL_MIN_SCORE = 0.7;

// Guardrail contextual grounding check — minimum grounding/relevance score (0-0.99)
// a home_repair answer needs against its search context before we treat it as valid.
export const GUARDRAIL_GROUNDING_THRESHOLD = 0.5;
export const GUARDRAIL_RELEVANCE_THRESHOLD = 0.5;

// S3 bucket for user-uploaded photos (auto-deleted after 24 h)
export const UPLOAD_BUCKET_NAME = 'home-repair-agent-uploads';

// Cognito User Pool
export const COGNITO_USER_POOL_NAME = 'HomeRepairAgentUserPool';

// Cognito hosted-UI domain prefix — must be globally unique across all AWS accounts
export const COGNITO_DOMAIN_PREFIX = 'home-repair-agent';

// UserInfo database schema name within the existing Aurora cluster
export const USER_INFO_SCHEMA = 'userinfo';

// iOS app bundle identifier — used as the JWT audience for Apple identity token validation
export const IOS_BUNDLE_ID = 'com.homerepairsus.app';

// Custom domain
export const DOMAIN_NAME    = 'homerepairsus.com';
export const API_DOMAIN     = `api.${DOMAIN_NAME}`;
export const HOSTED_ZONE_ID = 'Z06200071CTT0TYQJ5X8D';
