import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';
import { AWS_REGION, RAG_DB_CLUSTER_ID, RAG_DB_NAME } from './constants';

interface RagDatabaseStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
}

export class RagDatabaseStack extends cdk.Stack {
  public readonly dbCluster: rds.DatabaseCluster;
  public readonly dbSecret: secretsmanager.ISecret;
  public readonly dbSecurityGroup: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props: RagDatabaseStackProps) {
    super(scope, id, { ...props, env: { ...props.env, region: AWS_REGION } });

    const { vpc } = props;

    this.dbSecurityGroup = new ec2.SecurityGroup(this, 'DbSecurityGroup', {
      vpc,
      description: 'Allow PostgreSQL from within VPC',
      allowAllOutbound: false,
    });
    this.dbSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(5432),
      'PostgreSQL from VPC'
    );

    // Aurora Serverless v2 is required — Bedrock Knowledge Base only accepts Aurora cluster ARNs,
    // not standard RDS instance ARNs.
    this.dbCluster = new rds.DatabaseCluster(this, 'RagDatabase', {
      clusterIdentifier: RAG_DB_CLUSTER_ID,
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_16_4,
      }),
      writer: rds.ClusterInstance.serverlessV2('Writer'),
      serverlessV2MinCapacity: 0.5,
      serverlessV2MaxCapacity: 4,
      credentials: rds.Credentials.fromGeneratedSecret('homerepair_admin', {
        secretName: `/${RAG_DB_CLUSTER_ID}/db-credentials`,
      }),
      defaultDatabaseName: RAG_DB_NAME.toLowerCase(),
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      securityGroups: [this.dbSecurityGroup],
      storageEncrypted: true,
      backup: { retention: cdk.Duration.days(7) },
      removalPolicy: cdk.RemovalPolicy.SNAPSHOT,
    });

    this.dbSecret = this.dbCluster.secret!;

    new cdk.CfnOutput(this, 'DbEndpoint', {
      value: this.dbCluster.clusterEndpoint.hostname,
      exportName: 'HomeRepairRagDbEndpoint',
    });

    new cdk.CfnOutput(this, 'DbSecretArn', {
      value: this.dbSecret.secretArn,
      exportName: 'HomeRepairRagDbSecretArn',
    });

    new cdk.CfnOutput(this, 'DbClusterArn', {
      value: this.dbCluster.clusterArn,
      exportName: 'HomeRepairRagDbClusterArn',
    });
  }
}
