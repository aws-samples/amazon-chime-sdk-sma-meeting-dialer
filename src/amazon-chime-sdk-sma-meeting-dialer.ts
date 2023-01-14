import { App, CfnOutput, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import {
  PSTNAudio,
  S3Resources,
  Database,
  Infrastructure,
  Cognito,
  Site,
  DistributionResources,
} from '.';

export class SMAMeetingDialer extends Stack {
  constructor(scope: Construct, id: string, props: StackProps = {}) {
    super(scope, id, props);

    const database = new Database(this, 'Database');

    const distribution = new DistributionResources(this, 'Distribution');

    const pstnAudio = new PSTNAudio(this, 'PSTNAudio', {
      meetingTable: database.meetingTable,
    });

    const allowedDomain = this.node.tryGetContext('AllowedDomain');
    const cognito = new Cognito(this, 'Cognito', {
      allowedDomain: allowedDomain,
    });

    const infrastructure = new Infrastructure(this, 'Infrastructure', {
      meetingTable: database.meetingTable,
      userPool: cognito.userPool,
    });

    new Site(this, 'Site', {
      apiUrl: infrastructure.apiUrl,
      userPool: cognito.userPool,
      userPoolClient: cognito.userPoolClient,
      distribution: distribution.distribution,
      siteBucket: distribution.siteBucket,
    });

    const triggerBucket = new S3Resources(this, 'S3Resources', {
      fromNumber: pstnAudio.smaPhoneNumber,
      sipMediaApplicationId: pstnAudio.sipMediaApplicationId,
      meetingTable: database.meetingTable,
      distribution: distribution.distribution,
    });

    new CfnOutput(this, 'API_URL', { value: infrastructure.apiUrl });
    new CfnOutput(this, 'USER_POOL_REGION', { value: cognito.userPoolRegion });
    new CfnOutput(this, 'USER_POOL_ID', { value: cognito.userPool.userPoolId });
    new CfnOutput(this, 'USER_POOL_CLIENT', {
      value: cognito.userPoolClient.userPoolClientId,
    });
    new CfnOutput(this, 'siteBucket', {
      value: distribution.siteBucket.bucketName,
    });
    new CfnOutput(this, 'site', {
      value: distribution.distribution.distributionDomainName,
    });

    new CfnOutput(this, 'pstnPhoneNumber', {
      value: pstnAudio.smaPhoneNumber,
    });

    new CfnOutput(this, 'triggerBucket', {
      value: triggerBucket.triggerBucket.bucketName,
    });

    new CfnOutput(this, 'uploadToS3', {
      value: `aws s3 cp trigger.json s3://${triggerBucket.triggerBucket.bucketName}`,
    });
  }
}

const devEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const app = new App();

new SMAMeetingDialer(app, 'SMAMeetingDialer', { env: devEnv });

app.synth();
