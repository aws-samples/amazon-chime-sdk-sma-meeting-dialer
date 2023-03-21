import os
import decimal
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

# Set LOG_LEVEL using environment variable, fallback to INFO if not present
logger = logging.getLogger()
try:
    LOG_LEVEL = os.environ['LOG_LEVEL']
    if LOG_LEVEL not in ['INFO', 'DEBUG']:
        LOG_LEVEL = 'INFO'
except BaseException:
    LOG_LEVEL = 'INFO'
logger.setLevel(LOG_LEVEL)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)
    

def handler(event, context):
    global LOG_PREFIX
    LOG_PREFIX = 'Join Meeting: '

    logger.info('%s RECV Event: %s', LOG_PREFIX, json.dumps(event, indent=4))
  
    body = json.loads(event['body'])
    event_id = body['EventId']
    meeting_passcode = body['MeetingPasscode']
    phone_number = body['PhoneNumber']

    try:
        event_info = meeting_table.get_item(Key={"EventId": event_id, "MeetingPasscode": meeting_passcode})
    except Exception as error:
        logger.error('%s Error getting meeting info: %s', LOG_PREFIX, error)
        response['statusCode'] = 500
        logger.info('%s Response: %s', LOG_PREFIX, json.dumps(response, indent=4))
        return response
    logger.info('%s Event info: %s', LOG_PREFIX, json.dumps(event_info, cls=DecimalEncoder, indent=4))
    logger.info('%s MeetingPasscode: %s', LOG_PREFIX, meeting_passcode)
    logger.info('%s EventId: %s', LOG_PREFIX, event_id)
    logger.info('%s PhoneNumber: %s', LOG_PREFIX, phone_number)

    if 'Item' in event_info:
        if event_info['Item']['MeetingPasscode'] == meeting_passcode and event_info['Item']['EventId'] == event_id:
            meeting_info = create_meeting(event_id, phone_number)
            response_info = {
                'Meeting': meeting_info['Meeting'],
                'Attendee': meeting_info['Attendees'][0]
            }
            logger.info('%s Updating meeting info for event %s', LOG_PREFIX, event_id)
            logger.info('%s Meeting info: %s', LOG_PREFIX, json.dumps(meeting_info, indent=4))
            update_response = meeting_table.update_item(
                Key={"EventId": event_id, "MeetingPasscode": meeting_passcode},
                UpdateExpression="set JoinMethod = :j, MeetingId = :m, AttendeeId = :a",
                ExpressionAttributeValues={":j": 'Web',  ":m": meeting_info['Meeting']['MeetingId'], ":a": meeting_info['Attendees'][0]['AttendeeId']},
                ReturnValues="UPDATED_NEW"),
            logger.info('%s Update response: %s', LOG_PREFIX, json.dumps(update_response, indent=4))
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
    logger.info('%s Creating meeting for event %s', LOG_PREFIX, event_id)
    try:
        meeting_info = chime_sdk_meeting_client.create_meeting_with_attendees(
            ClientRequestToken=event_id,
            MediaRegion='us-east-1',
            ExternalMeetingId=event_id,
            Attendees=[{
                'ExternalUserId': phone_number
            }]
        )
        logger.info('%s Created Meeting: %s', LOG_PREFIX, json.dumps(meeting_info, indent=4))
        return meeting_info
    except Exception as error:
        logger.error('%s Error creating meeting: %s', LOG_PREFIX, error)
        raise error
