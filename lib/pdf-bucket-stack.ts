import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import { AWS_REGION, PDF_SOURCE_BUCKET_NAME } from './constants';

export class PdfBucketStack extends cdk.Stack {
  public readonly bucket: s3.Bucket;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, { ...props, env: { ...props?.env, region: AWS_REGION } });

    this.bucket = new s3.Bucket(this, 'PdfSourceBucket', {
      bucketName: PDF_SOURCE_BUCKET_NAME,
      versioned: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      // EventBridge integration lets other stacks react to S3 events without
      // creating a circular dependency between bucket and notification Lambda
      eventBridgeEnabled: true,
    });

    new cdk.CfnOutput(this, 'PdfBucketName', {
      value: this.bucket.bucketName,
      exportName: 'HomeRepairPdfBucketName',
    });

    new cdk.CfnOutput(this, 'PdfBucketArn', {
      value: this.bucket.bucketArn,
      exportName: 'HomeRepairPdfBucketArn',
    });
  }
}
