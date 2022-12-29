import os
import json
import logging
import time
import urllib.parse
from random import randint
import boto3
from botocore.exceptions import ClientError

chime_sdk_meeting_client = boto3.client('chime-sdk-meetings')
chime_sdk_voice_client = boto3.client('chime-sdk-voice')
s3_client = boto3.client('s3')
ses_client = boto3.client('ses')
dynamo_client = boto3.resource('dynamodb')

FROM_NUMBER = os.environ['FROM_NUMBER']
SIP_MEDIA_APPLICATION_ID = os.environ['SIP_MEDIA_APPLICATION_ID']
FROM_EMAIL = os.environ['FROM_EMAIL']
MEETING_TABLE = os.environ['MEETING_TABLE']

meeting_table = dynamo_client.Table(MEETING_TABLE)

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
    participant_list = []
    for participant in request_info['Participants']:
        logger.info('Adding attendee %s', participant['PhoneNumber'])
        participant_list.append({"Name":  participant.get('Name', 'None'), "PhoneNumber": participant['PhoneNumber'], 'Email':  participant.get('Email', 'None')})
        attendee_list.append({
            'ExternalUserId': participant['PhoneNumber'],
        })
    logger.info('Attendee List: %s', json.dumps(attendee_list))
    logger.info('Participant List: %s', json.dumps(participant_list))
    logger.info('Creating meeting:  %s', request_info['EventId'])
    meeting_info = chime_sdk_meeting_client.create_meeting_with_attendees(
        ClientRequestToken=str(request_info['EventId']),
        MediaRegion='us-east-1',
        ExternalMeetingId=str(request_info['EventId']),
        Attendees=attendee_list
    )

    for index, participant in enumerate(participant_list):
        participant_list[index]['JoinToken'] = meeting_info['Attendees'][index]['JoinToken']
        participant_list[index]['AttendeeId'] = meeting_info['Attendees'][index]['AttendeeId']
    
    logger.info('Participant List: %s', json.dumps(participant_list))
    logger.info('Meeting Info:  %s', json.dumps(meeting_info))
    for attendee in participant_list:
        logger.info('Calling attendee at %s for meeting %s', attendee['PhoneNumber'], request_info['EventId'])
        logger.info('Join Token: %s', attendee['JoinToken'])
        meeting_passcode = randint(100000, 999999)
        meeting_table.put_item(Item={
            'EventId': request_info['EventId'],
            'MeetingId': meeting_info['Meeting']['MeetingId'],
            'AttendeeId': attendee['AttendeeId'],
            'JoinToken': attendee['JoinToken'],
            'MeetingPasscode': meeting_passcode,
            'PhoneNumber':  attendee['PhoneNumber'],
            'TTL':  int(time.time() + 6000)
            })
        if (attendee['Email'] != 'None' and FROM_EMAIL != ''):
            send_email(request_info['EventId'], attendee['Email'], meeting_passcode)
        chime_sdk_voice_client.create_sip_media_application_call(
            FromPhoneNumber=FROM_NUMBER,
            ToPhoneNumber=attendee['PhoneNumber'],
            SipMediaApplicationId=SIP_MEDIA_APPLICATION_ID,
            ArgumentsMap={
                'meeting_id': meeting_info['Meeting']['MeetingId'],
                'attendee_id': attendee['AttendeeId'],
                'join_token': attendee['JoinToken'],
                'event_id': str(request_info['EventId'])
            }
        )


def send_email(event_id, to_email, meeting_passcode):
    try:
        ses_client.send_email(
            Source=FROM_EMAIL,
            Destination={
                'ToAddresses': [
                    to_email,
                ],
            },
            Message={
                'Subject': {
                    'Data': 'Amazon Chime SDK Meeting Invitation - ' + str(event_id),
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': 
                        (
                            'A meeting has been started. /nTo join the meeting:/n+' + str(FROM_NUMBER) +
                            ',,' + str(meeting_passcode) + '/nhttps://link.to/meetingId'
                        ),
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data':
                        (
                            '<p>A meeting has been started.</p><p>To join the meeting:</p><p>' +
                            str(FROM_NUMBER) + ',,' + str(meeting_passcode) +
                            '<p><a href="https://link.to/meeting">https://link.to/meetingId</a></p>'
                        ),
                        'Charset': 'UTF-8'
                        }
                    }
                },
        )
    except Exception as error:
        logger.error('Error sending email: %s', error)
        raise error