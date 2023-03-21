import os
import json
import logging
import decimal
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

chime_sdk_meeting_client = boto3.client('chime-sdk-meetings')
dynamo_client = boto3.resource('dynamodb')

MEETING_TABLE = os.environ['MEETING_TABLE']

meeting_table = dynamo_client.Table(MEETING_TABLE)
response = {
    'statusCode': 200,
    'headers': {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': True,
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Content-Type': 'application/json'
    }
}


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)


# Set LOG_LEVEL using environment variable, fallback to INFO if not present
logger = logging.getLogger()
try:
    LOG_LEVEL = os.environ['LOG_LEVEL']
    if LOG_LEVEL not in ['INFO', 'DEBUG']:
        LOG_LEVEL = 'INFO'
except BaseException:
    LOG_LEVEL = 'INFO'
logger.setLevel(LOG_LEVEL)


def handler(event, context):
    global LOG_PREFIX
    LOG_PREFIX = 'Query Meeting: '
    logger.info('%s RECV Event: %s', LOG_PREFIX, json.dumps(event, indent=4))
  
    body = json.loads(event['body'])

    if body.get('meetingId'):
        logger.info('%s Querying for meetingId: %s', LOG_PREFIX, body['meetingId'])
        query_response = meeting_table.query(
          IndexName='MeetingIdIndex',
          KeyConditionExpression=Key('MeetingId').eq(body['meetingId'])
          )
        logger.info('%s Query Response: %s', LOG_PREFIX, json.dumps(query_response, cls=DecimalEncoder, indent=4))
        if query_response['Count'] > 0:
            response['body'] = json.dumps(query_response['Items'], cls=DecimalEncoder)
            response['statusCode'] = 200
            logger.info('%s Response: %s', LOG_PREFIX, json.dumps(response, indent=4))
            return response
        else:
            response['statusCode'] = 404
            logger.info('%s Response: %s', LOG_PREFIX, json.dumps(response, indent=4))
            return response
    elif body.get('attendeeId') and body.get('meeting_id'):
        logger.info('%s Querying for meetingId: %s and attendeeId: %s', LOG_PREFIX, body['meeting_id'], body['attendeeId'])
        query_response = meeting_table.query(
            IndexName='MeetingIdIndex',
            KeyConditionExpression=(
                Key('MeetingId').eq(body['meetingId']) &
                Key('AttendeeId').eq(body['attendeeId'])
            )
        )
        logger.info('%s Query Response: %s', LOG_PREFIX, json.dumps(query_response, cls=DecimalEncoder, indent=4))
        if query_response['Count'] > 0:
            response['body'] = json.dumps(query_response['Item'])
            response['statusCode'] = 200
            logger.info('%s Response: %s', LOG_PREFIX, json.dumps(response, indent=4))
            return response
        else:
            response['statusCode'] = 404
            logger.info('%s Response: %s', LOG_PREFIX, json.dumps(response, indent=4))
            return response
    else:
        response['body'] = json.dumps({'message': 'MeetingID is required'})
        logger.info('%s Response: %s', LOG_PREFIX, json.dumps(response, indent=4))
        response['statusCode'] = 404
