import { Duration } from 'aws-cdk-lib';
import {
  RestApi,
  LambdaIntegration,
  EndpointType,
  MethodLoggingLevel,
  CognitoUserPoolsAuthorizer,
  AuthorizationType,
} from 'aws-cdk-lib/aws-apigateway';
import { Distribution } from 'aws-cdk-lib/aws-cloudfront';
import { IUserPool } from 'aws-cdk-lib/aws-cognito';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import {
  ManagedPolicy,
  Role,
  PolicyStatement,
  PolicyDocument,
  ServicePrincipal,
} from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime, Code, Function } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

interface InfrastructureProps {
  readonly userPool: IUserPool;
  readonly meetingTable: Table;
  fromNumber: string;
  fromEmail: string;
  sipMediaApplicationId: string;
  distribution: Distribution;
  logLevel: string;
}

export class Infrastructure extends Construct {
  public readonly apiUrl: string;
  public createMeetingHandler: Function;
  public joinMeetingHandler: Function;
  public queryMeetingHandler: Function;
  public endMeetingHandler: Function;

  constructor(scope: Construct, id: string, props: InfrastructureProps) {
    super(scope, id);

    const infrastructureRole = new Role(this, 'infrastructureRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
      inlinePolicies: {
        ['chimePolicy']: new PolicyDocument({
          statements: [
            new PolicyStatement({
              resources: ['*'],
              actions: ['chime:*'],
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

    const createMeetingLambdaRole = new Role(this, 'createMeetingLambdaRole', {
      assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
      inlinePolicies: {
        ['chimePolicy']: new PolicyDocument({
          statements: [
            new PolicyStatement({
              resources: ['*'],
              actions: [
                'chime:CreateSipMediaApplicationCall',
                'chime:CreateMeetingWithAttendees',
                'ses:SendEmail',
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

    this.createMeetingHandler = new Function(this, 'createMeetingHandler', {
      code: Code.fromAsset('src/resources/createMeeting', {
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
      runtime: Runtime.PYTHON_3_12,
      architecture: Architecture.ARM_64,
      environment: {
        FROM_NUMBER: props.fromNumber,
        SIP_MEDIA_APPLICATION_ID: props.sipMediaApplicationId,
        FROM_EMAIL: props.fromEmail,
        MEETING_TABLE: props.meetingTable.tableName,
        DISTRIBUTION: props.distribution.distributionDomainName,
        LOG_LEVEL: props.logLevel,
      },
      role: createMeetingLambdaRole,
      timeout: Duration.seconds(60),
    });

    this.joinMeetingHandler = new Function(this, 'joinMeetingHandler', {
      code: Code.fromAsset('src/resources/joinMeeting', {
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
      role: infrastructureRole,
      timeout: Duration.seconds(60),
    });

    props.meetingTable.grantReadWriteData(this.joinMeetingHandler);

    this.endMeetingHandler = new Function(this, 'endMeetingHandler', {
      code: Code.fromAsset('src/resources/endMeeting', {
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
      role: infrastructureRole,
      timeout: Duration.seconds(60),
    });

    props.meetingTable.grantReadWriteData(this.endMeetingHandler);

    this.queryMeetingHandler = new Function(this, 'queryMeetingHandler', {
      code: Code.fromAsset('src/resources/queryMeeting', {
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
      role: infrastructureRole,
      timeout: Duration.seconds(60),
    });

    props.meetingTable.grantReadWriteData(this.queryMeetingHandler);

    const api = new RestApi(this, 'smaMeetingDialerApi', {
      defaultCorsPreflightOptions: {
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
        ],
        allowMethods: ['OPTIONS', 'POST'],
        allowCredentials: true,
        allowOrigins: ['*'],
      },
      deployOptions: {
        loggingLevel: MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
      },
      endpointConfiguration: {
        types: [EndpointType.REGIONAL],
      },
    });

    const auth = new CognitoUserPoolsAuthorizer(this, 'auth', {
      cognitoUserPools: [props.userPool],
    });

    const join = api.root.addResource('join');
    const end = api.root.addResource('end');
    const query = api.root.addResource('query');
    const create = api.root.addResource('create');

    const joinIntegration = new LambdaIntegration(this.joinMeetingHandler);
    const endIntegration = new LambdaIntegration(this.endMeetingHandler);
    const queryIntegration = new LambdaIntegration(this.queryMeetingHandler);
    const createIntegration = new LambdaIntegration(this.createMeetingHandler);

    join.addMethod('POST', joinIntegration, {
      authorizer: auth,
      authorizationType: AuthorizationType.COGNITO,
    });
    end.addMethod('POST', endIntegration, {
      authorizer: auth,
      authorizationType: AuthorizationType.COGNITO,
    });
    query.addMethod('POST', queryIntegration, {
      authorizer: auth,
      authorizationType: AuthorizationType.COGNITO,
    });
    create.addMethod('POST', createIntegration, {
      authorizer: auth,
      authorizationType: AuthorizationType.COGNITO,
    });

    this.apiUrl = api.url;
  }
}
