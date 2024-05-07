import { Duration, Stack } from 'aws-cdk-lib';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import {
  ServicePrincipal,
  Role,
  ManagedPolicy,
  PolicyDocument,
  PolicyStatement,
} from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime, Function, Code } from 'aws-cdk-lib/aws-lambda';
import {
  ChimeSipMediaApp,
  ChimeSipRule,
  ChimePhoneNumber,
  PhoneProductType,
  PhoneNumberType,
  TriggerType,
} from 'cdk-amazon-chime-resources';
import { Construct } from 'constructs';

export interface ChimeSipMediaAppProps {
  meetingTable: Table;
  logLevel: string;
}

export class PSTNAudio extends Construct {
  public sipMediaApplicationId: string;
  public smaPhoneNumber: string;
  public smaHandler: Function;

  constructor(scope: Construct, id: string, props: ChimeSipMediaAppProps) {
    super(scope, id);

    const smaLambdaRole = new Role(this, 'smaLambdaRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
      inlinePolicies: {
        ['chimePolicy']: new PolicyDocument({
          statements: [
            new PolicyStatement({
              resources: ['*'],
              actions: [
                'chime:DeleteAttendee',
                'chime:DeleteMeeting',
                'chime:ListAttendees',
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

    this.smaHandler = new Function(this, 'smaHandler', {
      code: Code.fromAsset('src/resources/smaHandler', {
        bundling: {
          image: Runtime.PYTHON_3_12.bundlingImage,
          command: [
            'bash',
            '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output',
          ],
        },
      }),
      handler: 'index.handler',
      environment: {
        MEETING_TABLE: props.meetingTable.tableName,
        LOG_LEVEL: props.logLevel,
      },
      runtime: Runtime.PYTHON_3_12,
      architecture: Architecture.ARM_64,
      role: smaLambdaRole,
      timeout: Duration.seconds(60),
    });

    props.meetingTable.grantReadWriteData(this.smaHandler);

    const sipMediaApp = new ChimeSipMediaApp(this, 'SipMediaApplication', {
      endpoint: this.smaHandler.functionArn,
      region: Stack.of(this).region,
    });

    const phoneNumber = new ChimePhoneNumber(this, 'PhoneNumber', {
      phoneState: 'AZ',
      phoneNumberType: PhoneNumberType.LOCAL,
      phoneProductType: PhoneProductType.SMA,
    });

    new ChimeSipRule(this, 'SipRule', {
      triggerType: TriggerType.TO_PHONE_NUMBER,
      triggerValue: phoneNumber.phoneNumber,
      targetApplications: [
        {
          region: Stack.of(this).region,
          priority: 1,
          sipMediaApplicationId: sipMediaApp.sipMediaAppId,
        },
      ],
    });

    this.sipMediaApplicationId = sipMediaApp.sipMediaAppId;
    this.smaPhoneNumber = phoneNumber.phoneNumber;
  }
}
