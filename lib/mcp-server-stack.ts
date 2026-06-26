import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';
import { AWS_REGION } from './constants';

interface McpServerStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  dbSecret: secretsmanager.ISecret;
}

export class McpServerStack extends cdk.Stack {
  public readonly mcpFn: lambda.IFunction;

  constructor(scope: Construct, id: string, props: McpServerStackProps) {
    super(scope, id, { ...props, env: { ...props.env, region: AWS_REGION } });

    const { vpc, dbSecret } = props;

    // PythonFunction bundles requirements.txt automatically using Docker.
    // Ensure Docker Desktop is running before deploying this stack.
    this.mcpFn = new PythonFunction(this, 'McpServerFn', {
      functionName: 'HomeRepairAgent-McpServer',
      entry: path.join(__dirname, '../lambdas/homerepair-mcp-server'),
      runtime: lambda.Runtime.PYTHON_3_12,
      index: 'handler.py',
      handler: 'handler',
      timeout: cdk.Duration.seconds(30),
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      environment: {
        DB_SECRET_ARN: dbSecret.secretArn,
      },
    });

    dbSecret.grantRead(this.mcpFn);

    new cdk.CfnOutput(this, 'McpFunctionArn', {
      value: this.mcpFn.functionArn,
      exportName: 'HomeRepairMcpFunctionArn',
    });
  }
}
