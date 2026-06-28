import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as cr from 'aws-cdk-lib/custom-resources';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';
import { AWS_REGION } from './constants';

interface UserInfoDatabaseStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
  dbCluster: rds.DatabaseCluster;
  dbSecret: secretsmanager.ISecret;
}

export class UserInfoDatabaseStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: UserInfoDatabaseStackProps) {
    super(scope, id, { ...props, env: { ...props.env, region: AWS_REGION } });

    const { vpc, dbSecret } = props;

    // Lambda runs inside the VPC so it can reach Aurora on port 5432 directly —
    // no bastion host or DBeaver tunnel needed.
    const initFn = new NodejsFunction(this, 'InitUserDbFn', {
      functionName: 'HomeRepairAgent-init-user-db',
      entry: path.join(__dirname, '../lambdas/init-user-db/index.ts'),
      handler: 'handler',
      runtime: lambda.Runtime.NODEJS_20_X,
      timeout: cdk.Duration.minutes(2),
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      bundling: {
        // Copy the SQL file into the Lambda bundle so readFileSync can find it at runtime
        commandHooks: {
          beforeBundling: () => [],
          beforeInstall: () => [],
          afterBundling: (inputDir, outputDir) => [
            `cp ${inputDir}/dbscripts/user_info_postgres.sql ${outputDir}/user_info_postgres.sql`,
          ],
        },
      },
      environment: {
        DB_SECRET_ARN: dbSecret.secretArn,
      },
    });

    dbSecret.grantRead(initFn);

    initFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['secretsmanager:GetSecretValue'],
      resources: [dbSecret.secretArn],
    }));

    // Custom resource — triggers the Lambda once on first deploy (RequestType: Create)
    const provider = new cr.Provider(this, 'InitUserDbProvider', {
      onEventHandler: initFn,
    });

    new cdk.CustomResource(this, 'InitUserDbResource', {
      serviceToken: provider.serviceToken,
      // Changing this version string forces the schema to re-run if you ever need it
      properties: { SchemaVersion: '2' },
    });

    new cdk.CfnOutput(this, 'UserInfoSchemaStatus', {
      value: 'userinfo schema initialized in existing Aurora cluster',
    });
  }
}
