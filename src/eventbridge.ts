import { Duration } from 'aws-cdk-lib';
import { Rule } from 'aws-cdk-lib/aws-events';
import { LambdaFunction } from 'aws-cdk-lib/aws-events-targets';
import { Architecture, Runtime, Code, Function } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface EventBridgeResourcesProps {
  logLevel: string;
}

export class EventBridgeResources extends Construct {
  public eventBridgeLambda: Function;

  constructor(scope: Construct, id: string, props: EventBridgeResourcesProps) {
    super(scope, id);

    this.eventBridgeLambda = new Function(this, 'eventBridgeLambda', {
      code: Code.fromAsset('src/resources/eventBridge', {
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
        LOG_LEVEL: props.logLevel,
      },
      runtime: Runtime.PYTHON_3_9,
      architecture: Architecture.ARM_64,
      timeout: Duration.seconds(60),
    });

    const chimeSdkRule = new Rule(this, 'chimeSdkRule', {
      eventPattern: {
        source: ['aws.chime'],
      },
    });
    chimeSdkRule.addTarget(new LambdaFunction(this.eventBridgeLambda));
  }
}
