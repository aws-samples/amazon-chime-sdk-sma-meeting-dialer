import os
import json
import logging
import boto3
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
    LOG_PREFIX = 'End Meeting: '
    logger.info('RECV %s \nEvent: %s', LOG_PREFIX, json.dumps(event, indent=4))
  
    body = json.loads(event['body'])
    if body['meetingId']:
        logger.info('Deleting meeting: %s', body['meetingId'])
        delete_meeting_response = delete_meeting(body['meetingId'])
        if delete_meeting_response:
            response['body'] = json.dumps({'message': 'Meeting deleted successfully'})
            response['statusCode'] = 200
            return response
        else:
            response['body'] = json.dumps({'message': 'Unable to delete meeting'})
            response['statusCode'] = 503
            return response
    else:
        response['body'] = json.dumps({'message': 'Meeting ID not provided'})
        response['statusCode'] = 404
        return response


def delete_meeting(meeting_id):
    try:
        delete_meeting_response = chime_sdk_meeting_client.delete_meeting(
            MeetingId=meeting_id
        )
        logger.info('Delete meeting response: %s', delete_meeting_response)
        return True
    except ClientError as error:
        logger.error('Error deleting meeting: %s', error)
        return False
