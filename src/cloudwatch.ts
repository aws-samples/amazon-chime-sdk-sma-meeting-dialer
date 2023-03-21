import { Stack } from 'aws-cdk-lib';
import {
  Dashboard,
  LogQueryVisualizationType,
  LogQueryWidget,
} from 'aws-cdk-lib/aws-cloudwatch';
import { Function } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

interface CloudWatchResourcesProps {
  createMeetingHandler: Function;
  joinMeetingHandler: Function;
  queryMeetingHandler: Function;
  endMeetingHandler: Function;
  smaHandler: Function;
}

export class CloudWatchResources extends Construct {
  public dashboard: Dashboard;

  constructor(scope: Construct, id: string, props: CloudWatchResourcesProps) {
    super(scope, id);

    this.dashboard = new Dashboard(this, 'Dashboard', {
      dashboardName: 'SMADialer',
    });

    this.dashboard.addWidgets(
      new LogQueryWidget({
        title: 'SMADialer Logs',
        logGroupNames: [
          props.createMeetingHandler.logGroup.logGroupName,
          props.createMeetingHandler.logGroup.logGroupName,
          props.joinMeetingHandler.logGroup.logGroupName,
          props.queryMeetingHandler.logGroup.logGroupName,
          props.smaHandler.logGroup.logGroupName,
        ],
        width: 24,
        region: Stack.of(this).region,
        view: LogQueryVisualizationType.TABLE,
        queryLines: [
          'fields @timestamp, @message',
          'sort @timestamp desc',
          'limit 200',
        ],
      }),
    );
  }
}
