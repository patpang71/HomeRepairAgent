import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import { Construct } from 'constructs';
import { AWS_REGION, BEDROCK_AGENT_MODEL_ID, UPLOAD_BUCKET_NAME } from './constants';

interface LangGraphAgentStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  mcpFunctionArn: string;
  dbSecret: secretsmanager.ISecret;
}

export class LangGraphAgentStack extends cdk.Stack {
  public readonly agentFn: lambda.IFunction;

  constructor(scope: Construct, id: string, props: LangGraphAgentStackProps) {
    super(scope, id, { ...props, env: { ...props.env, region: AWS_REGION } });

    const { vpc, mcpFunctionArn, dbSecret } = props;

    // ── Session table ────────────────────────────────────────────────────────
    const sessionTable = new dynamodb.Table(this, 'SessionTable', {
      tableName: 'HomeRepairAgentSessions',
      partitionKey: { name: 'sessionId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: 'ttl',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ── Lambda ───────────────────────────────────────────────────────────────
    const agentSg = new ec2.SecurityGroup(this, 'AgentLambdaSg', {
      vpc,
      description: 'LangGraph agent Lambda - outbound to Bedrock, Lambda, DynamoDB',
      allowAllOutbound: true,
    });

    this.agentFn = new PythonFunction(this, 'LangGraphAgentFn', {
      functionName: 'HomeRepairAgent-LangGraphAgent',
      entry: path.join(__dirname, '../lambdas/langgraph-agent'),
      index: 'handler.py',
      handler: 'handler',
      runtime: lambda.Runtime.PYTHON_3_12,
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [agentSg],
      environment: {
        BEDROCK_MODEL_ID: BEDROCK_AGENT_MODEL_ID,
        MCP_FUNCTION_NAME: 'HomeRepairAgent-McpServer',
        SESSION_TABLE_NAME: sessionTable.tableName,
        UPLOAD_BUCKET_NAME,
        TAVILY_API_KEY_PARAM: '/HomeRepairAgent/Tavily/ApiKey',
        DB_SECRET_ARN: dbSecret.secretArn,
        LOG_LEVEL: 'INFO',
      },
    });

    sessionTable.grantReadWriteData(this.agentFn);
    dbSecret.grantRead(this.agentFn);

    this.agentFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['lambda:InvokeFunction'],
      resources: [mcpFunctionArn],
    }));

    this.agentFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel'],
      resources: ['*'],
    }));

    this.agentFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['s3:GetObject'],
      resources: [`arn:aws:s3:::${UPLOAD_BUCKET_NAME}/uploads/*`],
    }));

    this.agentFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ssm:GetParameter'],
      resources: [`arn:aws:ssm:${AWS_REGION}:*:parameter/HomeRepairAgent/Tavily/*`],
    }));

    new cdk.CfnOutput(this, 'AgentFunctionArn', {
      value: this.agentFn.functionArn,
      exportName: 'HomeRepairAgentFunctionArn',
    });
  }
}
