import {
  BedrockAgentClient,
  StartIngestionJobCommand,
} from '@aws-sdk/client-bedrock-agent';

const client = new BedrockAgentClient({});

export const handler = async (event: unknown): Promise<void> => {
  const knowledgeBaseId = process.env.KNOWLEDGE_BASE_ID;
  const dataSourceId = process.env.DATA_SOURCE_ID;

  if (!knowledgeBaseId || !dataSourceId) {
    throw new Error('KNOWLEDGE_BASE_ID and DATA_SOURCE_ID env vars are required');
  }

  console.log('Starting ingestion job', { knowledgeBaseId, dataSourceId, event });

  const command = new StartIngestionJobCommand({
    knowledgeBaseId,
    dataSourceId,
    // Unique token prevents duplicate jobs if Lambda retries
    clientToken: `sync-${Date.now()}`,
  });

  const response = await client.send(command);
  console.log('Ingestion job started', { ingestionJobId: response.ingestionJob?.ingestionJobId });
};
