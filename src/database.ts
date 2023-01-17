import { RemovalPolicy } from 'aws-cdk-lib';
import {
  AttributeType,
  Table,
  BillingMode,
  TableEncryption,
  ProjectionType,
} from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class Database extends Construct {
  public meetingTable: Table;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.meetingTable = new Table(this, 'callRecordsTable', {
      partitionKey: {
        name: 'EventId',
        type: AttributeType.STRING,
      },
      sortKey: {
        name: 'MeetingPasscode',
        type: AttributeType.STRING,
      },
      removalPolicy: RemovalPolicy.DESTROY,
      encryption: TableEncryption.AWS_MANAGED,
      timeToLiveAttribute: 'TTL',
      billingMode: BillingMode.PAY_PER_REQUEST,
    });

    this.meetingTable.addGlobalSecondaryIndex({
      projectionType: ProjectionType.ALL,
      indexName: 'MeetingIdIndex',
      partitionKey: {
        name: 'MeetingId',
        type: AttributeType.STRING,
      },
    });
  }
}
