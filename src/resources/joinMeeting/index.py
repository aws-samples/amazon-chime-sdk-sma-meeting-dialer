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
    LOG_PREFIX = 'Join Meeting'
    logger.info('RECV %s \nEvent: %s', LOG_PREFIX, json.dumps(event, indent=4))
  
    body = json.loads(event['body'])
    event_id = body['EventId']
    meeting_passcode = body['MeetingPasscode']
    phone_number = body['PhoneNumber']

    try:
        event_info = meeting_table.get_item(Key={"EventId": event_id, "MeetingPasscode": meeting_passcode})
    except Exception as error:
        logger.error('Error getting meeting info: %s', error)
        response['statusCode'] = 500
        return response
    logger.info('Meeting info: %s', event_info)
    logger.info('MeetingPasscode: %s  Type: %s', meeting_passcode, type(meeting_passcode))
    logger.info('PhoneNumber: %s  Type: %s', phone_number, type(phone_number))
    logger.info('EventId: %s  Type: %s', event_id, type(event_id))
    if 'Item' in event_info:
        if event_info['Item']['MeetingPasscode'] == meeting_passcode and event_info['Item']['EventId'] == event_id:
            meeting_info = create_meeting(event_id, phone_number)
            response_info = {
                'Meeting': meeting_info['Meeting'],
                'Attendee': meeting_info['Attendees'][0]
            }
            update_response = meeting_table.update_item(
                Key={"EventId": event_id, "MeetingPasscode": meeting_passcode},
                UpdateExpression="set JoinMethod = :j, MeetingId = :m, AttendeeId = :a",
                ExpressionAttributeValues={":j": 'Web',  ":m": meeting_info['Meeting']['MeetingId'], ":a": meeting_info['Attendees'][0]['AttendeeId']},
                ReturnValues="UPDATED_NEW"),
            logger.info('Update response: %s', json.dumps(update_response, indent=4))
            response['body'] = json.dumps(response_info)
            response['statusCode'] = 200
            return response
        else:
            response['statusCode'] = 403
            return response
    else:
        response['statusCode'] = 404
        return response


def create_meeting(event_id, phone_number):
    logger.info('Creating meeting for event %s', event_id)
    meeting_info = chime_sdk_meeting_client.create_meeting_with_attendees(
        ClientRequestToken=event_id,
        MediaRegion='us-east-1',
        ExternalMeetingId=event_id,
        Attendees=[{
            'ExternalUserId': phone_number
        }]
    )
    return meeting_info
