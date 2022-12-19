import { App } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { SMAMeetingDialer } from '../src/amazon-chime-sdk-sma-meeting-dialer';

test('Snapshot', () => {
  const app = new App();
  const stack = new SMAMeetingDialer(app, 'test');

  const template = Template.fromStack(stack);
  expect(template.toJSON()).toMatchSnapshot();
});
