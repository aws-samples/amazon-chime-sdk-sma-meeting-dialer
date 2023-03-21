import { App, CfnOutput, Stack, StackProps } from 'aws-cdk-lib';
import {
  IUserPool,
  IUserPoolClient,
  UserPool,
  UserPoolClient,
} from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';
import {
  PSTNAudio,
  S3Resources,
  Database,
  Infrastructure,
  Cognito,
  Site,
  DistributionResources,
  CloudWatchResources,
} from '.';

interface SMAMeetingDialerProps extends StackProps {
  userPool?: string;
  userPoolClient?: string;
  userPoolRegion?: string;
  allowedDomain: string;
  fromEmail: string;
}

interface CognitoOutput {
  userPool: IUserPool;
  userPoolClient: IUserPoolClient;
  userPoolRegion: string;
}

export class SMAMeetingDialer extends Stack {
  constructor(scope: Construct, id: string, props: SMAMeetingDialerProps) {
    super(scope, id, props);

    const database = new Database(this, 'Database');

    const distribution = new DistributionResources(this, 'Distribution');

    const pstnAudio = new PSTNAudio(this, 'PSTNAudio', {
      meetingTable: database.meetingTable,
    });

    let cognito: CognitoOutput;

    if (props.userPoolRegion && props.userPool && props.userPoolClient) {
      cognito = {
        userPoolRegion: props.userPoolRegion,
        userPool: UserPool.fromUserPoolArn(this, 'userPoolId', props.userPool),
        userPoolClient: UserPoolClient.fromUserPoolClientId(
          this,
          'userPoolClientId',
          props.userPoolClient,
        ),
      };
    } else {
      cognito = new Cognito(this, 'Cognito', {
        allowedDomain: props.allowedDomain,
      });
    }

    const infrastructure = new Infrastructure(this, 'Infrastructure', {
      meetingTable: database.meetingTable,
      userPool: cognito.userPool,
      distribution: distribution.distribution,
      fromNumber: pstnAudio.smaPhoneNumber,
      sipMediaApplicationId: pstnAudio.sipMediaApplicationId,
      fromEmail: props.fromEmail,
    });

    const cloudwatchResources = new CloudWatchResources(
      this,
      'CloudWatchResources',
      {
        joinMeetingHandler: infrastructure.joinMeetingHandler,
        endMeetingHandler: infrastructure.endMeetingHandler,
        queryMeetingHandler: infrastructure.queryMeetingHandler,
        createMeetingHandler: infrastructure.createMeetingHandler,
        smaHandler: pstnAudio.smaHandler,
      },
    );

    new Site(this, 'Site', {
      apiUrl: infrastructure.apiUrl,
      userPool: cognito.userPool,
      userPoolClient: cognito.userPoolClient,
      distribution: distribution.distribution,
      siteBucket: distribution.siteBucket,
    });

    const triggerBucket = new S3Resources(this, 'S3Resources', {
      createMeetingHandler: infrastructure.createMeetingHandler,
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

    new CfnOutput(this, 'Dashboard', {
      value: cloudwatchResources.dashboard.dashboardName,
    });
  }
}

const devEnv = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const stackProps = {
  userPool: process.env.USER_POOL || '',
  userPoolClient: process.env.USER_POOL_CLIENT || '',
  userPoolRegion: process.env.USER_POOL_REGION || '',
  allowedDomain: process.env.ALLOWED_DOMAIN || '',
  fromEmail: process.env.FROM_EMAIL || '',
};

const app = new App();

new SMAMeetingDialer(app, 'SMAMeetingDialer', { ...stackProps, env: devEnv });

app.synth();
