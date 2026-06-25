import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as apigwv2Authorizers from 'aws-cdk-lib/aws-apigatewayv2-authorizers';
import * as apigwv2Integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as route53Targets from 'aws-cdk-lib/aws-route53-targets';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';
import {
  API_DOMAIN,
  AWS_REGION,
  BEDROCK_AGENT_MODEL_ID,
  COGNITO_DOMAIN_PREFIX,
  COGNITO_USER_POOL_NAME,
  DOMAIN_NAME,
  UPLOAD_BUCKET_NAME,
} from './constants';

interface ApiStackProps extends cdk.StackProps {
  vpc: ec2.Vpc;
}

export class ApiStack extends cdk.Stack {
  public readonly api: apigwv2.HttpApi;
  public readonly userPool: cognito.UserPool;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, { ...props, env: { ...props.env, region: AWS_REGION } });

    const { vpc } = props;

    // ── Cognito User Pool ────────────────────────────────────────────────────
    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: COGNITO_USER_POOL_NAME,
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      autoVerify: { email: true },
      standardAttributes: {
        email: { required: true, mutable: true },
        givenName: { required: false, mutable: true },
        familyName: { required: false, mutable: true },
      },
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Apple Sign-In credentials — populate these before deploying:
    //   aws ssm put-parameter --name /HomeRepairAgent/Apple/ServicesId --value "com.yourcompany.homerepair" --type String
    //   aws ssm put-parameter --name /HomeRepairAgent/Apple/TeamId      --value "XXXXXXXXXX"                --type String
    //   aws ssm put-parameter --name /HomeRepairAgent/Apple/KeyId       --value "XXXXXXXXXX"                --type String
    //   aws secretsmanager create-secret --name HomeRepairAgent/Apple/PrivateKey \
    //       --secret-string "$(cat AuthKey_XXXXXXXXXX.p8)"
    const appleServicesId = ssm.StringParameter.valueForStringParameter(this, '/HomeRepairAgent/Apple/ServicesId');
    const appleTeamId     = ssm.StringParameter.valueForStringParameter(this, '/HomeRepairAgent/Apple/TeamId');
    const appleKeyId      = ssm.StringParameter.valueForStringParameter(this, '/HomeRepairAgent/Apple/KeyId');
    // CloudFormation resolves this dynamic reference at deploy time — never appears in plaintext in the template
    const applePrivateKey = '{{resolve:secretsmanager:HomeRepairAgent/Apple/PrivateKey}}';

    const appleIdP = new cognito.UserPoolIdentityProviderApple(this, 'AppleIdP', {
      userPool: this.userPool,
      clientId: appleServicesId,
      teamId: appleTeamId,
      keyId: appleKeyId,
      privateKey: applePrivateKey,
      scopes: ['name', 'email'],
      attributeMapping: {
        email: cognito.ProviderAttribute.APPLE_EMAIL,
        givenName: cognito.ProviderAttribute.APPLE_FIRST_NAME,
        familyName: cognito.ProviderAttribute.APPLE_LAST_NAME,
      },
    });

    // callbackUrls must match the URL scheme registered in your iOS app's Info.plist
    const userPoolClient = new cognito.UserPoolClient(this, 'UserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: 'HomeRepairAgentIos',
      generateSecret: false,
      supportedIdentityProviders: [cognito.UserPoolClientIdentityProvider.APPLE],
      oAuth: {
        flows: { authorizationCodeGrant: true },
        scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
        callbackUrls: ['homerepairagent://callback'],
      },
    });
    userPoolClient.node.addDependency(appleIdP);

    // Hosted UI — iOS uses this OAuth2 endpoint to exchange Apple tokens for Cognito JWTs
    this.userPool.addDomain('CognitoDomain', {
      cognitoDomain: { domainPrefix: COGNITO_DOMAIN_PREFIX },
    });

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
    const uploadUrlFn = new NodejsFunction(this, 'UploadUrlFn', {
      entry: path.join(__dirname, '../lambdas/upload-url/index.ts'),
      handler: 'handler',
      runtime: lambda.Runtime.NODEJS_20_X,
      timeout: cdk.Duration.seconds(10),
      environment: {
        UPLOAD_BUCKET_NAME: uploadBucket.bucketName,
      },
    });
    uploadBucket.grantPut(uploadUrlFn);

    // ── Lambda: POST /chat ───────────────────────────────────────────────────
    const chatLambdaSg = new ec2.SecurityGroup(this, 'ChatLambdaSg', {
      vpc,
      description: 'Chat Lambda — outbound to Bedrock and RDS VPC endpoints',
      allowAllOutbound: true,
    });

    const chatFn = new NodejsFunction(this, 'ChatFn', {
      entry: path.join(__dirname, '../lambdas/chat/index.ts'),
      handler: 'handler',
      runtime: lambda.Runtime.NODEJS_20_X,
      timeout: cdk.Duration.seconds(60),
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [chatLambdaSg],
      environment: {
        UPLOAD_BUCKET_NAME: uploadBucket.bucketName,
        BEDROCK_AGENT_MODEL_ID,
      },
    });

    uploadBucket.grantRead(chatFn);

    chatFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel', 'bedrock:InvokeAgent'],
      resources: ['*'],
    }));

    // ── HTTP API Gateway ─────────────────────────────────────────────────────
    this.api = new apigwv2.HttpApi(this, 'HttpApi', {
      apiName: 'HomeRepairAgentApi',
      corsPreflight: {
        allowOrigins: ['*'],
        allowMethods: [apigwv2.CorsHttpMethod.POST],
        allowHeaders: ['Authorization', 'Content-Type'],
      },
    });

    const authorizer = new apigwv2Authorizers.HttpJwtAuthorizer(
      'CognitoAuthorizer',
      `https://cognito-idp.${AWS_REGION}.amazonaws.com/${this.userPool.userPoolId}`,
      { jwtAudience: [userPoolClient.userPoolClientId] },
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
      integration: new apigwv2Integrations.HttpLambdaIntegration('ChatIntegration', chatFn),
      authorizer,
    });

    // ── Custom Domain (api.homerepairus.com) ─────────────────────────────────
    // Domain was registered in Route 53 — look up the existing hosted zone.
    const hostedZone = route53.HostedZone.fromLookup(this, 'HostedZone', {
      domainName: DOMAIN_NAME,
    });

    // ACM issues a free TLS certificate; DNS validation auto-creates the required
    // Route 53 record so no manual approval step is needed.
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

    // Alias record: api.homerepairus.com → API Gateway regional endpoint
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

    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      exportName: 'HomeRepairAgentUserPoolId',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: userPoolClient.userPoolClientId,
      exportName: 'HomeRepairAgentUserPoolClientId',
    });

    new cdk.CfnOutput(this, 'CognitoDomainUrl', {
      value: `https://${COGNITO_DOMAIN_PREFIX}.auth.${AWS_REGION}.amazoncognito.com`,
      exportName: 'HomeRepairAgentCognitoDomainUrl',
    });
  }
}
