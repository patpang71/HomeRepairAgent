import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';
import { AWS_REGION } from './constants';

export class VpcStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly eicEndpoint: ec2.CfnInstanceConnectEndpoint;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, { ...props, env: { ...props?.env, region: AWS_REGION } });

    this.vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
        {
          name: 'Isolated',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          cidrMask: 24,
        },
      ],
    });

    // Gateway endpoint — free and required for S3 access from private subnets
    this.vpc.addGatewayEndpoint('S3Endpoint', {
      service: ec2.GatewayVpcEndpointAwsService.S3,
    });

    // Interface endpoints allow Lambda and Bedrock services to operate within the VPC
    // without routing through the public internet
    const endpointSg = new ec2.SecurityGroup(this, 'VpcEndpointSg', {
      vpc: this.vpc,
      description: 'Allow HTTPS from within VPC to interface endpoints',
      allowAllOutbound: false,
    });
    endpointSg.addIngressRule(ec2.Peer.ipv4(this.vpc.vpcCidrBlock), ec2.Port.tcp(443));

    const privateSubnets = { subnets: this.vpc.privateSubnets };

    this.vpc.addInterfaceEndpoint('SecretsManagerEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
      subnets: privateSubnets,
      securityGroups: [endpointSg],
    });

    this.vpc.addInterfaceEndpoint('BedrockRuntimeEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
      subnets: privateSubnets,
      securityGroups: [endpointSg],
    });

    this.vpc.addInterfaceEndpoint('BedrockAgentRuntimeEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.BEDROCK_AGENT_RUNTIME,
      subnets: privateSubnets,
      securityGroups: [endpointSg],
    });

    // bedrock.amazonaws.com — required for Bedrock Knowledge Base to connect to RDS pgvector
    this.vpc.addInterfaceEndpoint('BedrockEndpoint', {
      service: ec2.InterfaceVpcEndpointAwsService.BEDROCK,
      subnets: privateSubnets,
      securityGroups: [endpointSg],
    });

    // EC2 Instance Connect Endpoint — allows local machine to tunnel TCP to RDS (port 5432)
    // without a bastion host or any open inbound ports.
    // Usage: aws ec2-instance-connect open-tunnel \
    //   --instance-connect-endpoint-id <EicEndpointId> \
    //   --remote-port 5432 \
    //   --remote-host <RDS endpoint> \
    //   --local-port 5432
    // Then connect via: psql -h 127.0.0.1 -p 5432 -U homerepair_admin -d homerepairragdb
    this.eicEndpoint = new ec2.CfnInstanceConnectEndpoint(this, 'EicEndpoint', {
      subnetId: this.vpc.privateSubnets[0].subnetId,
      preserveClientIp: false,
    });

    new cdk.CfnOutput(this, 'VpcId', { value: this.vpc.vpcId });
    new cdk.CfnOutput(this, 'EicEndpointId', {
      value: this.eicEndpoint.attrId,
      exportName: 'HomeRepairEicEndpointId',
    });
  }
}
