import { Duration } from 'aws-cdk-lib';
import {
  RestApi,
  LambdaIntegration,
  EndpointType,
  MethodLoggingLevel,
  CognitoUserPoolsAuthorizer,
  AuthorizationType,
} from 'aws-cdk-lib/aws-apigateway';
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
}

export class Infrastructure extends Construct {
  public readonly apiUrl: string;

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

    const joinMeetingHandler = new Function(this, 'joinMeetingHandler', {
      code: Code.fromAsset('src/resources/joinMeeting', {
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
      environment: {
        MEETING_TABLE: props.meetingTable.tableName,
      },
      runtime: Runtime.PYTHON_3_9,
      architecture: Architecture.ARM_64,
      role: infrastructureRole,
      timeout: Duration.seconds(60),
    });

    props.meetingTable.grantReadWriteData(joinMeetingHandler);

    const endMeetingHandler = new Function(this, 'endMeetingHandler', {
      code: Code.fromAsset('src/resources/endMeeting', {
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
      environment: {
        MEETING_TABLE: props.meetingTable.tableName,
      },
      runtime: Runtime.PYTHON_3_9,
      architecture: Architecture.ARM_64,
      role: infrastructureRole,
      timeout: Duration.seconds(60),
    });

    props.meetingTable.grantReadWriteData(endMeetingHandler);

    const queryMeetingHandler = new Function(this, 'queryMeetingHandler', {
      code: Code.fromAsset('src/resources/queryMeeting', {
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
      environment: {
        MEETING_TABLE: props.meetingTable.tableName,
      },
      runtime: Runtime.PYTHON_3_9,
      architecture: Architecture.ARM_64,
      role: infrastructureRole,
      timeout: Duration.seconds(60),
    });

    props.meetingTable.grantReadWriteData(queryMeetingHandler);

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

    const joinIntegration = new LambdaIntegration(joinMeetingHandler);
    const endIntegration = new LambdaIntegration(endMeetingHandler);
    const queryIntegration = new LambdaIntegration(queryMeetingHandler);

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

    this.apiUrl = api.url;
  }
}
