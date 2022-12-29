import { App, CfnOutput, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { PSTNAudio, S3Resources, Database } from '.';

export class SMAMeetingDialer extends Stack {
  constructor(scope: Construct, id: string, props: StackProps = {}) {
    super(scope, id, props);

    const database = new Database(this, 'Database');

    const pstnAudio = new PSTNAudio(this, 'PSTNAudio', {
      meetingTable: database.meetingTable,
    });

    const triggerBucket = new S3Resources(this, 'S3Resources', {
      fromNumber: pstnAudio.smaPhoneNumber,
      sipMediaApplicationId: pstnAudio.sipMediaApplicationId,
      meetingTable: database.meetingTable,
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
