import * as cdk from 'aws-cdk-lib';
import { AWS_REGION, PROJECT_NAME } from '../lib/constants';
import { ApiStack } from '../lib/api-stack';
import { KnowledgeBaseStack } from '../lib/knowledge-base-stack';
import { LangGraphAgentStack } from '../lib/langgraph-agent-stack';
import { McpServerStack } from '../lib/mcp-server-stack';
import { PdfBucketStack } from '../lib/pdf-bucket-stack';
import { RagDatabaseStack } from '../lib/rag-database-stack';
import { UserInfoDatabaseStack } from '../lib/user-info-database-stack';
import { VpcStack } from '../lib/vpc-stack';

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: AWS_REGION,
};

const vpcStack = new VpcStack(app, `${PROJECT_NAME}-Vpc`, { env });

const ragDatabaseStack = new RagDatabaseStack(app, `${PROJECT_NAME}-RagDatabase`, {
  env,
  vpc: vpcStack.vpc,
});
ragDatabaseStack.addDependency(vpcStack);

const pdfBucketStack = new PdfBucketStack(app, `${PROJECT_NAME}-PdfBucket`, { env });

const knowledgeBaseStack = new KnowledgeBaseStack(app, `${PROJECT_NAME}-KnowledgeBase`, {
  env,
  pdfBucket: pdfBucketStack.bucket,
  dbCluster: ragDatabaseStack.dbCluster,
  dbSecret: ragDatabaseStack.dbSecret,
});
knowledgeBaseStack.addDependency(ragDatabaseStack);
knowledgeBaseStack.addDependency(pdfBucketStack);

const userInfoDatabaseStack = new UserInfoDatabaseStack(app, `${PROJECT_NAME}-UserInfoDatabase`, {
  env,
  vpc: vpcStack.vpc,
  dbCluster: ragDatabaseStack.dbCluster,
  dbSecret: ragDatabaseStack.dbSecret,
});
userInfoDatabaseStack.addDependency(ragDatabaseStack);

const mcpServerStack = new McpServerStack(app, `${PROJECT_NAME}-McpServer`, {
  env,
  vpc: vpcStack.vpc,
  dbSecret: ragDatabaseStack.dbSecret,
});
mcpServerStack.addDependency(ragDatabaseStack);

const langGraphAgentStack = new LangGraphAgentStack(app, `${PROJECT_NAME}-LangGraphAgent`, {
  env,
  vpc: vpcStack.vpc,
  mcpFunctionArn: mcpServerStack.mcpFn.functionArn,
  dbSecret: ragDatabaseStack.dbSecret,
  knowledgeBaseId: knowledgeBaseStack.knowledgeBase.attrKnowledgeBaseId,
  knowledgeBaseArn: knowledgeBaseStack.knowledgeBase.attrKnowledgeBaseArn,
});
langGraphAgentStack.addDependency(vpcStack);
langGraphAgentStack.addDependency(mcpServerStack);
langGraphAgentStack.addDependency(knowledgeBaseStack);

const apiStack = new ApiStack(app, `${PROJECT_NAME}-Api`, {
  env,
  agentFn: langGraphAgentStack.agentFn,
});
apiStack.addDependency(langGraphAgentStack);

app.synth();
