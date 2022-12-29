import { RemovalPolicy } from 'aws-cdk-lib';
import { AttributeType, Table, BillingMode } from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class Database extends Construct {
  public meetingTable: Table;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.meetingTable = new Table(this, 'callRecordsTable', {
      partitionKey: {
        name: 'MeetingPasscode',
        type: AttributeType.NUMBER,
      },
      removalPolicy: RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'TTL',
      billingMode: BillingMode.PAY_PER_REQUEST,
    });
  }
}
