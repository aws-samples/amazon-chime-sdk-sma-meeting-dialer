import { RemovalPolicy } from 'aws-cdk-lib';
import { Distribution } from 'aws-cdk-lib/aws-cloudfront';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Function } from 'aws-cdk-lib/aws-lambda';
import { S3EventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { Bucket, EventType } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

interface S3ResourcesProps {
  fromNumber: string;
  sipMediaApplicationId: string;
  meetingTable: Table;
  distribution: Distribution;
  createMeetingHandler: Function;
}
export class S3Resources extends Construct {
  public triggerBucket: Bucket;

  constructor(scope: Construct, id: string, props: S3ResourcesProps) {
    super(scope, id);

    this.triggerBucket = new Bucket(this, 'triggerBucket', {
      publicReadAccess: false,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    this.triggerBucket.grantRead(props.createMeetingHandler);
    props.meetingTable.grantReadWriteData(props.createMeetingHandler);

    props.createMeetingHandler.addEventSource(
      new S3EventSource(this.triggerBucket, {
        events: [EventType.OBJECT_CREATED],
      }),
    );
  }
}
