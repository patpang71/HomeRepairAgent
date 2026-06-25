import { randomUUID } from 'crypto';
import { APIGatewayProxyEventV2WithJWTAuthorizer, APIGatewayProxyResultV2 } from 'aws-lambda';

export const handler = async (
  event: APIGatewayProxyEventV2WithJWTAuthorizer,
): Promise<APIGatewayProxyResultV2> => {
  const userId = event.requestContext.authorizer.jwt.claims.sub as string;
  const { message, sessionId, imageKey } = JSON.parse(event.body ?? '{}');

  if (!message) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'message is required' }),
    };
  }

  // TODO: load user home profile from RDS using userId
  // TODO: if imageKey provided, fetch image bytes from S3 and pass as multimodal input
  // TODO: invoke Bedrock Agent with message + home context
  // TODO: parse agent response and extract structured product recommendations

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionId: sessionId ?? randomUUID(),
      message: 'Agent response placeholder — Bedrock integration coming next.',
      products: [],
    }),
  };
};
