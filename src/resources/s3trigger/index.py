import os
import json
import logging
import boto3
import urllib.parse
from botocore.exceptions import ClientError

chime_sdk_meeting_client = boto3.client('chime-sdk-meetings')
chime_sdk_voice_client = boto3.client('chime-sdk-voice')
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
    log_prefix = 'S3Trigger'
    logger.info('RECV %s Event: %s', log_prefix, json.dumps(event))

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        meeting_request = s3_client.get_object(Bucket=bucket, Key=key)
        logger.info("CONTENT TYPE: %s", meeting_request['ContentType'])
    except Exception as error:
        logger.error('S3 GetObject Error: %s', error)
        raise error

    request_info = json.loads(meeting_request['Body'].read().decode('utf-8'))
    logger.info('RECV Request Info: %s ', json.dumps(request_info))

    attendee_list = []
    for participant in request_info['Participants']:
        logger.info('Adding attendee %s', participant['PhoneNumber'])
        attendee_list.append({
            'ExternalUserId': participant['PhoneNumber'],
        })
    logger.info('Attendee List: %s', json.dumps(attendee_list))

    logger.info('Creating meeting:  %s', request_info['EventId'])
    meeting_info = chime_sdk_meeting_client.create_meeting_with_attendees(
        ClientRequestToken=str(request_info['EventId']),
        MediaRegion='us-east-1',
        ExternalMeetingId=str(request_info['EventId']),
        Attendees=attendee_list
    )

    logger.info('Meeting Info:  %s', json.dumps(meeting_info))

    for attendee in meeting_info['Attendees']:
        logger.info('Calling attendee at %s for meeting %s', attendee['ExternalUserId'], request_info['EventId'])
        logger.info('Join Token: %s', attendee['JoinToken'])
        chime_sdk_voice_client.create_sip_media_application_call(
            FromPhoneNumber=FROM_NUMBER,
            ToPhoneNumber=attendee['ExternalUserId'],
            SipMediaApplicationId=SIP_MEDIA_APPLICATION_ID,
            ArgumentsMap={
                'meeting_id': meeting_info['Meeting']['MeetingId'],
                'attendee_id': attendee['AttendeeId'],
                'join_token': attendee['JoinToken'],
                'event_id': str(request_info['EventId'])
            }

        )
