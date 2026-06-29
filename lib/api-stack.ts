import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as apigwv2Authorizers from 'aws-cdk-lib/aws-apigatewayv2-authorizers';
import * as apigwv2Integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
import {
  API_DOMAIN,
  AWS_REGION,
  DOMAIN_NAME,
  HOSTED_ZONE_ID,
  IOS_BUNDLE_ID,
  UPLOAD_BUCKET_NAME,
} from './constants';

interface ApiStackProps extends cdk.StackProps {
  agentFn: lambda.IFunction;
}

export class ApiStack extends cdk.Stack {
  public readonly api: apigwv2.HttpApi;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, { ...props, env: { ...props.env, region: AWS_REGION } });

    const { agentFn } = props;

    // ── S3 Upload Bucket ─────────────────────────────────────────────────────
    const uploadBucket = new s3.Bucket(this, 'UploadBucket', {
      bucketName: UPLOAD_BUCKET_NAME,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      lifecycleRules: [{ expiration: cdk.Duration.days(1), prefix: 'uploads/' }],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // ── Lambda: POST /upload-url ─────────────────────────────────────────────
    const uploadUrlFn = new PythonFunction(this, 'UploadUrlFn', {
      entry: path.join(__dirname, '../lambdas/upload-url'),
      index: 'handler.py',
      handler: 'handler',
      runtime: lambda.Runtime.PYTHON_3_12,
      timeout: cdk.Duration.seconds(10),
      environment: {
        UPLOAD_BUCKET_NAME: uploadBucket.bucketName,
      },
    });
    uploadBucket.grantPut(uploadUrlFn);

    // ── HTTP API Gateway ─────────────────────────────────────────────────────
    this.api = new apigwv2.HttpApi(this, 'HttpApi', {
      apiName: 'HomeRepairAgentApi',
      corsPreflight: {
        allowOrigins: ['*'],
        allowMethods: [apigwv2.CorsHttpMethod.POST],
        allowHeaders: ['Authorization', 'Content-Type'],
      },
    });

    // Validates Apple identity tokens directly — issuer is Apple, audience is the app bundle ID.
    // The iOS app gets these tokens from expo-apple-authentication and sends them as Bearer tokens.
    const authorizer = new apigwv2Authorizers.HttpJwtAuthorizer(
      'AppleAuthorizer',
      'https://appleid.apple.com',
      { jwtAudience: [IOS_BUNDLE_ID] },
    );

    this.api.addRoutes({
      path: '/upload-url',
      methods: [apigwv2.HttpMethod.POST],
      integration: new apigwv2Integrations.HttpLambdaIntegration('UploadUrlIntegration', uploadUrlFn),
      authorizer,
    });

    this.api.addRoutes({
      path: '/chat',
      methods: [apigwv2.HttpMethod.POST],
      integration: new apigwv2Integrations.HttpLambdaIntegration('ChatIntegration', agentFn),
      authorizer,
    });

    // ── Custom Domain (api.homerepairsus.com) ────────────────────────────────
    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, 'HostedZone', {
      hostedZoneId: HOSTED_ZONE_ID,
      zoneName: DOMAIN_NAME,
    });

    const certificate = new acm.Certificate(this, 'ApiCertificate', {
      domainName: API_DOMAIN,
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });

    const customDomain = new apigwv2.DomainName(this, 'CustomDomain', {
      domainName: API_DOMAIN,
      certificate,
    });

    new apigwv2.ApiMapping(this, 'ApiMapping', {
      api: this.api,
      domainName: customDomain,
    });

    new route53.ARecord(this, 'ApiAliasRecord', {
      zone: hostedZone,
      recordName: 'api',
      target: route53.RecordTarget.fromAlias(
        new route53Targets.ApiGatewayv2DomainProperties(
          customDomain.regionalDomainName,
          customDomain.regionalHostedZoneId,
        ),
      ),
    });

    // ── Outputs ──────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: `https://${API_DOMAIN}`,
      exportName: 'HomeRepairAgentApiUrl',
    });
  }
}
