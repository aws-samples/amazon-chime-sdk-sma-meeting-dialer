import os
import json
import logging
import boto3
import urllib.parse
from botocore.exceptions import ClientError

chime_sdk_meeting_client = boto3.client('chime-sdk-meetings')
chime_sdk_voice_client = boto3.client('chime=sdk-voice')
s3_client = boto3.client('s3')

FROM_NUMBER = os.environ['FROM_NUMBER']
SIP_MEDIA_APPLICATION_ID = os.environ['SIP_MEDIA_APPLICATION_ID']

logger = logging.getLogger()
try:
    log_level = os.environ['LogLevel']
    if log_level not in ['INFO', 'DEBUG']:
        log_level = 'INFO'
except BaseException:
    log_level = 'INFO'
logger.setLevel(log_level)


def handler(event, context):
    global log_prefix
    log_prefix = 'S3Trigger: '
    logger.info('RECV {%s} Event: {%s}', log_prefix, json.dumps(event))

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        meeting_request = s3_client.get_object(Bucket=bucket, Key=key)
        print("CONTENT TYPE: " + meeting_request['ContentType'])
    except Exception as error:
        print(error)
        print(f'Error getting object {key} from bucket {bucket}. Make sure they exist and your bucket is in the same region as this function.')
        raise error

    request_info = json.loads(meeting_request['Body'].read().decode('utf-8'))
    logger.info(request_info)

    attendee_list = []
    for participant in request_info['Participants']:
        attendee_list.append({
            'ExternalUserId': participant['PhoneNumber'],
        })

    meeting_info = chime_sdk_meeting_client.create_meeting_with_attendees(
        ClientRequestToken=request_info['EventId'],
        MediaRegion='us-east-1',
        ExternalMeetingId=request_info['EventId'],
        Attendees=attendee_list
    )

    for attendee in meeting_info['Attendees']:
        chime_sdk_voice_client.create_sip_media_application_call(
            FromPhoneNumber=FROM_NUMBER,
            ToPhoneNumber=attendee['ExternalUserId'],
            SipMediaApplicationId=SIP_MEDIA_APPLICATION_ID,
            ArgumentsMap={
                'meeting_id': meeting_info['Meeting']['MeetingId'],
                'attendee_id': attendee['AttendeeId'],
                'join_token': attendee['JoinToken'],
                'event_id': request_info['EventId']
            }

        )
