import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as cr from 'aws-cdk-lib/custom-resources';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';
import {
  AWS_REGION,
  BEDROCK_EMBEDDING_MODEL_ID,
  EMBEDDING_DIMENSIONS,
  KNOWLEDGE_BASE_NAME,
  RAG_DB_NAME,
} from './constants';

interface KnowledgeBaseStackProps extends cdk.StackProps {
  pdfBucket: s3.Bucket;
  dbCluster: rds.DatabaseCluster;
  dbSecret: secretsmanager.ISecret;
}

export class KnowledgeBaseStack extends cdk.Stack {
  public readonly knowledgeBase: bedrock.CfnKnowledgeBase;
  public readonly dataSource: bedrock.CfnDataSource;

  constructor(scope: Construct, id: string, props: KnowledgeBaseStackProps) {
    super(scope, id, { ...props, env: { ...props.env, region: AWS_REGION } });

    const { pdfBucket, dbCluster, dbSecret } = props;

    // IAM role that Bedrock assumes to read S3, call the embedding model, and access RDS credentials
    const kbRole = new iam.Role(this, 'KnowledgeBaseRole', {
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      description: 'Role assumed by Bedrock Knowledge Base for HomeRepairAgent',
    });

    pdfBucket.grantRead(kbRole);
    dbSecret.grantRead(kbRole);

    kbRole.addToPolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel'],
      resources: [
        `arn:aws:bedrock:${AWS_REGION}::foundation-model/${BEDROCK_EMBEDDING_MODEL_ID}`,
      ],
    }));

    kbRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'rds:DescribeDBClusters',
        'rds-data:ExecuteStatement',
        'rds-data:BatchExecuteStatement',
      ],
      resources: [dbCluster.clusterArn],
    }));

    // ── RAG DB schema init ───────────────────────────────────────────────────
    // Creates bedrock_integration schema + bedrock_kb table via RDS Data API.
    // Runs once on stack creation; subsequent deploys skip it.
    const initRagDbFn = new NodejsFunction(this, 'InitRagDbFn', {
      functionName: 'HomeRepairAgent-init-rag-db',
      entry: path.join(__dirname, '../lambdas/init-rag-db/index.ts'),
      handler: 'handler',
      runtime: lambda.Runtime.NODEJS_20_X,
      timeout: cdk.Duration.seconds(60),
      environment: {
        CLUSTER_ARN: dbCluster.clusterArn,
        SECRET_ARN: dbSecret.secretArn,
        DATABASE_NAME: RAG_DB_NAME.toLowerCase(),
        EMBEDDING_DIMENSIONS: String(EMBEDDING_DIMENSIONS),
      },
    });

    initRagDbFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['rds-data:ExecuteStatement'],
      resources: [dbCluster.clusterArn],
    }));
    dbSecret.grantRead(initRagDbFn);

    const initProvider = new cr.Provider(this, 'InitRagDbProvider', {
      onEventHandler: initRagDbFn,
    });

    const schemaInit = new cdk.CustomResource(this, 'InitRagDbSchema', {
      serviceToken: initProvider.serviceToken,
      properties: { SchemaVersion: '2' },
    });

    this.knowledgeBase = new bedrock.CfnKnowledgeBase(this, 'KnowledgeBase', {
      name: KNOWLEDGE_BASE_NAME,
      roleArn: kbRole.roleArn,
      knowledgeBaseConfiguration: {
        type: 'VECTOR',
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: `arn:aws:bedrock:${AWS_REGION}::foundation-model/${BEDROCK_EMBEDDING_MODEL_ID}`,
          embeddingModelConfiguration: {
            bedrockEmbeddingModelConfiguration: {
              dimensions: EMBEDDING_DIMENSIONS,
            },
          },
        },
      },
      storageConfiguration: {
        type: 'RDS',
        rdsConfiguration: {
          resourceArn: dbCluster.clusterArn,
          credentialsSecretArn: dbSecret.secretArn,
          databaseName: RAG_DB_NAME.toLowerCase(),
          tableName: 'bedrock_integration.bedrock_kb',
          fieldMapping: {
            primaryKeyField: 'id',
            vectorField: 'embedding',
            textField: 'chunks',
            metadataField: 'metadata',
          },
        },
      },
    });

    // kbRole.addToPolicy creates a separate AWS::IAM::Policy resource (DefaultPolicy).
    // CfnKnowledgeBase only gets a DependsOn on the Role itself (via roleArn), not on the
    // policy resource, so CloudFormation can start creating the KB before the policy is
    // attached. Bedrock validates rds:DescribeDBClusters at creation time and fails.
    // This explicit dependency ensures the policy is fully attached first.
    // Schema must exist before Bedrock validates the storage configuration
    this.knowledgeBase.node.addDependency(schemaInit);

    // DefaultPolicy (from addToPolicy) is a separate CFN resource — KB must also wait for it
    const defaultPolicy = kbRole.node.tryFindChild('DefaultPolicy');
    if (defaultPolicy) {
      this.knowledgeBase.node.addDependency(defaultPolicy);
    }

    this.dataSource = new bedrock.CfnDataSource(this, 'PdfDataSource', {
      name: 'HomeRepairPdfSource',
      knowledgeBaseId: this.knowledgeBase.attrKnowledgeBaseId,
      dataSourceConfiguration: {
        type: 'S3',
        s3Configuration: {
          bucketArn: pdfBucket.bucketArn,
        },
      },
      vectorIngestionConfiguration: {
        chunkingConfiguration: {
          chunkingStrategy: 'FIXED_SIZE',
          fixedSizeChunkingConfiguration: {
            maxTokens: 512,
            overlapPercentage: 20,
          },
        },
      },
    });

    // Lambda that calls StartIngestionJob when a PDF lands in S3 (via EventBridge)
    const triggerFn = new NodejsFunction(this, 'KbSyncTrigger', {
      functionName: 'HomeRepairAgent-trigger-kb-sync',
      entry: path.join(__dirname, '../lambdas/trigger-kb-sync/index.ts'),
      handler: 'handler',
      runtime: lambda.Runtime.NODEJS_20_X,
      timeout: cdk.Duration.seconds(30),
      environment: {
        KNOWLEDGE_BASE_ID: this.knowledgeBase.attrKnowledgeBaseId,
        DATA_SOURCE_ID: this.dataSource.attrDataSourceId,
      },
    });

    triggerFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:StartIngestionJob'],
      resources: [this.knowledgeBase.attrKnowledgeBaseArn],
    }));

    // EventBridge rule: fires when any object is PUT into the PDF bucket
    new events.Rule(this, 'PdfUploadRule', {
      description: 'Trigger KB sync when a PDF is uploaded to the source bucket',
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
        detail: {
          bucket: { name: [pdfBucket.bucketName] },
          object: { key: [{ suffix: '.pdf' }] },
        },
      },
      targets: [new targets.LambdaFunction(triggerFn)],
    });

    new cdk.CfnOutput(this, 'KnowledgeBaseId', {
      value: this.knowledgeBase.attrKnowledgeBaseId,
      exportName: 'HomeRepairKnowledgeBaseId',
    });

    new cdk.CfnOutput(this, 'DataSourceId', {
      value: this.dataSource.attrDataSourceId,
      exportName: 'HomeRepairDataSourceId',
    });
  }
}
