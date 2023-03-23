import { App } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { SMAMeetingDialer } from '../src/amazon-chime-sdk-sma-meeting-dialer';

test('Snapshot', () => {
  const app = new App();
  const stack = new SMAMeetingDialer(app, 'test', {
    fromEmail: 'test@example',
    allowedDomain: 'example.com',
    logLevel: '',
  });

  const template = Template.fromStack(stack);
  expect(template.toJSON()).toMatchSnapshot();
});

test('SnapshotCognito', () => {
  const app = new App({
    context: { AsteriskDeploy: 'y', AllowedDomain: 'example.com' },
  });
  const stack = new SMAMeetingDialer(app, 'test', {
    userPool:
      'arn:aws:cognito-idp:us-east-1:104621577074:userpool/us-east-1_z8UDEjm17',
    userPoolClient: 'string',
    userPoolRegion: 'string',
    fromEmail: '',
    allowedDomain: '',
    logLevel: 'info',
  });
  const template = Template.fromStack(stack);
  expect(template.toJSON()).toMatchSnapshot();
});
