import { RemovalPolicy, Duration } from 'aws-cdk-lib';
import {
  ServicePrincipal,
  PolicyDocument,
  PolicyStatement,
  ManagedPolicy,
  Role,
} from 'aws-cdk-lib/aws-iam';
import { Function, Runtime, Architecture, Code } from 'aws-cdk-lib/aws-lambda';
import { S3EventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { Bucket, EventType } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

interface S3ResourcesProps {
  fromNumber: string;
  sipMediaApplicationId: string;
}
export class S3Resources extends Construct {
  public triggerBucket: Bucket;

  constructor(scope: Construct, id: string, props: S3ResourcesProps) {
    super(scope, id);

    const s3TriggerLambdaRole = new Role(this, 's3TriggerLambdaRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
      inlinePolicies: {
        ['chimePolicy']: new PolicyDocument({
          statements: [
            new PolicyStatement({
              resources: ['*'],
              actions: [
                'chime:CreateSipMediaApplicationCall',
                'chime:CreateMeetingWithAttendees',
              ],
            }),
          ],
        }),
      },
      managedPolicies: [
        ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AWSLambdaBasicExecutionRole',
        ),
      ],
    });

    const s3TriggerLambda = new Function(this, 's3TriggerLambda', {
      code: Code.fromAsset('src/resources/s3trigger', {
        bundling: {
          image: Runtime.PYTHON_3_9.bundlingImage,
          command: [
            'bash',
            '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output',
          ],
        },
      }),
      handler: 'index.handler',
      runtime: Runtime.PYTHON_3_9,
      architecture: Architecture.ARM_64,
      environment: {
        FROM_NUMBER: props.fromNumber,
        SIP_MEDIA_APPLICATION_ID: props.sipMediaApplicationId,
      },
      role: s3TriggerLambdaRole,
      timeout: Duration.seconds(60),
    });

    this.triggerBucket = new Bucket(this, 'triggerBucket', {
      publicReadAccess: false,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    this.triggerBucket.grantRead(s3TriggerLambda);

    s3TriggerLambda.addEventSource(
      new S3EventSource(this.triggerBucket, {
        events: [EventType.OBJECT_CREATED],
      }),
    );
  }
}
