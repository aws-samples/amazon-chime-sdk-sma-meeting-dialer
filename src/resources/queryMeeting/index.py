import os
import json
import logging
import boto3
from decimal import *
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
        # 👇️ if passed in object is instance of Decimal
        # convert it to a string
        if isinstance(obj, Decimal):
            return str(obj)
        # 👇️ otherwise use the default behavior
        return json.JSONEncoder.default(self, obj)


# Set LogLevel using environment variable, fallback to INFO if not present
logger = logging.getLogger()
try:
    LOG_LEVEL = os.environ['LogLevel']
    if LOG_LEVEL not in ['INFO', 'DEBUG']:
        LOG_LEVEL = 'INFO'
except BaseException:
    LOG_LEVEL = 'INFO'
logger.setLevel(LOG_LEVEL)


def handler(event, context):
    global LOG_PREFIX
    LOG_PREFIX = 'Query Meeting: '
    logger.info('RECV %s \nEvent: %s', LOG_PREFIX, json.dumps(event, indent=4))
  
    body = json.loads(event['body'])

    if body.get('meetingId'):
        logger.info('Querying for meetingId: %s', body['meetingId'])
        query_response = meeting_table.query(
          IndexName='MeetingIdIndex',
          KeyConditionExpression=Key('MeetingId').eq(body['meetingId'])
          )
        logger.info('Query Response: %s', query_response)
        if query_response['Count'] > 0:
            response['body'] = json.dumps(query_response['Items'], cls=DecimalEncoder)
            response['statusCode'] = 200
            return response
        else:
            response['statusCode'] = 404
            return response
    elif body.get('attendeeId') and body.get('meeting_id'):
        logger.info('Querying for meetingId: %s and attendeeId: %s', body['meetingId'], body['attendeeId'])
        query_response = meeting_table.query(
            IndexName='MeetingIdIndex',
            KeyConditionExpression=(
                Key('MeetingId').eq(body['meetingId']) &
                Key('AttendeeId').eq(body['attendeeId'])
            )
        )
        logger.info('Query Response: %s', query_response)
        if query_response['Count'] > 0:
            response['body'] = json.dumps(query_response['Item'])
            response['statusCode'] = 200
            return response
        else:
            response['statusCode'] = 404
            return response
    else:
        response['body'] = json.dumps({'message': 'MeetingID is required'})
        response['statusCode'] = 404
