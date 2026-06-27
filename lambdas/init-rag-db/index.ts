import { RDSDataClient, ExecuteStatementCommand } from '@aws-sdk/client-rds-data';

const rds = new RDSDataClient({});

const CLUSTER_ARN = process.env.CLUSTER_ARN!;
const SECRET_ARN  = process.env.SECRET_ARN!;
const DATABASE    = process.env.DATABASE_NAME!;
const DIMENSIONS  = process.env.EMBEDDING_DIMENSIONS!;

async function exec(sql: string): Promise<void> {
  await rds.send(new ExecuteStatementCommand({
    resourceArn: CLUSTER_ARN,
    secretArn: SECRET_ARN,
    database: DATABASE,
    sql,
  }));
}

export const handler = async (event: { RequestType: string }): Promise<{ PhysicalResourceId: string }> => {
  if (event.RequestType !== 'Create') {
    return { PhysicalResourceId: 'init-rag-db-schema' };
  }

  await exec('CREATE EXTENSION IF NOT EXISTS vector');
  await exec('CREATE SCHEMA IF NOT EXISTS bedrock_integration');
  await exec(`
    CREATE TABLE IF NOT EXISTS bedrock_integration.bedrock_kb (
      id       uuid PRIMARY KEY,
      embedding vector(${DIMENSIONS}),
      chunks   text,
      metadata json
    )
  `);
  await exec(`
    CREATE INDEX IF NOT EXISTS bedrock_kb_embedding_idx
    ON bedrock_integration.bedrock_kb
    USING hnsw (embedding vector_cosine_ops)
  `);
  await exec(`
    CREATE INDEX IF NOT EXISTS bedrock_kb_chunks_idx
    ON bedrock_integration.bedrock_kb
    USING gin (to_tsvector('simple', chunks))
  `);

  console.log('RAG DB schema initialized successfully');
  return { PhysicalResourceId: 'init-rag-db-schema' };
};
