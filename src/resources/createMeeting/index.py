import os
import decimal
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
DISTRIBUTION = os.environ['DISTRIBUTION']

meeting_table = dynamo_client.Table(MEETING_TABLE)

logger = logging.getLogger()
try:
    LOG_LEVEL = os.environ['LOG_LEVEL']
    if LOG_LEVEL not in ['INFO', 'DEBUG', 'WARN', 'ERROR']:
        LOG_LEVEL = 'INFO'
except BaseException:
    LOG_LEVEL = 'INFO'
logger.setLevel(LOG_LEVEL)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)


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


def handler(event, context):
    global LOG_PREFIX
    LOG_PREFIX = 'Create Meeting: '
    if 'Records' in event:
        logger.info('%s RECV Event: %s', LOG_PREFIX, json.dumps(event))
        participants, event_id = get_records(event)
        create_meeting(participants, event_id)
    else:
        logger.info('%s RECV Event: %s', LOG_PREFIX, json.dumps(event))
        participant_request = json.loads(event['body'])
        logger.info('%s Participant Request: %s', LOG_PREFIX, json.dumps(participant_request, indent=4))
        participants = [{
            "Name": participant_request['attendeeName'],
            "PhoneNumber": participant_request['attendeePhoneNumber'],
            "Email": participant_request['attendeeEmail'],
            "CallParticipant": participant_request['attendeeCall']
        }]
        event_id = participant_request['eventId']
        passcode = create_meeting(participants, event_id)
        if passcode:
            response['body'] = json.dumps({'message': 'Participant added successfully', 'passcode': passcode})
            response['statusCode'] = 200
            return response
        response['body'] = json.dumps({'message': 'Unable to add participant'})
        response['statusCode'] = 503
        return response


def create_meeting(participants, event_id):
    attendee_list = []
    participant_list = []
    for participant in participants:
        logger.info('%s Adding attendee %s', LOG_PREFIX, participant['PhoneNumber'])
        participant_list.append({
            "Name":  participant.get('Name', 'None'),
            "PhoneNumber": participant['PhoneNumber'],
            'Email':  participant.get('Email', 'None'),
            'CallParticipant': participant.get('CallParticipant', 'None')})
        attendee_list.append({
            'ExternalUserId': participant['PhoneNumber'],
        })
    logger.info('%s Attendee List: %s', LOG_PREFIX, json.dumps(attendee_list))
    logger.info('%s Participant List: %s', LOG_PREFIX, json.dumps(participant_list))
    logger.info('%s Event ID: %s', LOG_PREFIX, event_id)

    try:
        meeting_info = chime_sdk_meeting_client.create_meeting_with_attendees(
            ClientRequestToken=str(event_id),
            MediaRegion='us-east-1',
            ExternalMeetingId=str(event_id),
            Attendees=attendee_list
        )
    except Exception as error:
        logger.error('%s Error creating meeting: %s', LOG_PREFIX, error)
        raise error
    for index, participant in enumerate(participant_list):
        participant_list[index]['JoinToken'] = meeting_info['Attendees'][index]['JoinToken']
        participant_list[index]['AttendeeId'] = meeting_info['Attendees'][index]['AttendeeId']
        participant_list[index]['Attendee'] = meeting_info['Attendees'][index]
        participant_list[index]['MeetingId'] = meeting_info['Meeting']['MeetingId']

    logger.info('%s Meeting Info: %s', LOG_PREFIX, json.dumps(meeting_info))

    for attendee in participant_list:
        meeting_passcode = randint(100000, 999999)
        meeting_object = {
            'EventId': str(event_id),
            'MeetingId': meeting_info['Meeting']['MeetingId'],
            'MeetingPasscode': str(meeting_passcode),
            'PhoneNumber':  attendee['PhoneNumber'],
            'Name': attendee['Name'],
            'TTL':  int(time.time() + 86400)
        }
        update_db(meeting_object)
        if ((attendee['Email'] != '' or attendee['Email'] != 'None') and FROM_EMAIL != ''):
            send_email(event_id, attendee['Email'], meeting_passcode)
        if attendee['CallParticipant'] is True:
            call_participant(attendee, event_id, meeting_passcode)
    if len(participants) == 1:
        return meeting_passcode
    else:
        return True


def update_db(meeting_object):
    try:
        logger.info('%s Updating Database: %s', LOG_PREFIX, json.dumps(meeting_object, cls=DecimalEncoder))
        meeting_table.put_item(Item=meeting_object)
        logger.info('%s Updated Database', LOG_PREFIX)
        return
    except Exception as error:
        logger.error('%s Error updating Database: %s', LOG_PREFIX, error)
        raise error


def get_records(event):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    logger.info('%s Getting S3 Object: %s/%s', LOG_PREFIX, bucket, key)
    try:
        meeting_request = s3_client.get_object(Bucket=bucket, Key=key)
        logger.info("%s CONTENT TYPE: %s", LOG_PREFIX, meeting_request['ContentType'])
    except Exception as error:
        logger.error('%s S3 GetObject Error: %s', LOG_PREFIX, error)
        raise error

    request_info = json.loads(meeting_request['Body'].read().decode('utf-8'))
    logger.info('%s S3 GetObject Info: %s', LOG_PREFIX, json.dumps(request_info))
    return request_info['Participants'], request_info['EventId']


def call_participant(attendee, event_id, meeting_passcode):
    logger.info('%s Calling %s for meeting %s', LOG_PREFIX, attendee['PhoneNumber'], event_id)
    try:
        chime_sdk_voice_client.create_sip_media_application_call(
            FromPhoneNumber=FROM_NUMBER,
            ToPhoneNumber=attendee['PhoneNumber'],
            SipMediaApplicationId=SIP_MEDIA_APPLICATION_ID,
            ArgumentsMap={
                'meeting_id': attendee['MeetingId'],
                'attendee_id': attendee['Attendee']['AttendeeId'],
                'join_token': attendee['Attendee']['JoinToken'],
                'event_id': str(event_id),
                'meeting_passcode': str(meeting_passcode),
                'phone_number': attendee['PhoneNumber'],
            }
        )
    except Exception as error:
        logger.error('%s Error calling attendee: %s', LOG_PREFIX, error)
        raise error


def send_email(event_id, to_email, meeting_passcode):
    logger.info('%s Sending email to %s for meeting %s', LOG_PREFIX, to_email, event_id)
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
                            'A meeting has been started. /nTo join the meeting:/n+' +
                            str(FROM_NUMBER) + ',,' + str(event_id) + ',,' + str(meeting_passcode) +
                            '/nhttp://' + DISTRIBUTION + '/meeting?eventId=' + str(event_id) + '&passcode=' + str(meeting_passcode)
                        ),
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data':
                        (
                            '<p>A meeting has been started.</p><p>To join the meeting:</p><p>' +
                            str(FROM_NUMBER) + ',,' + str(event_id) + ',,' + str(meeting_passcode) +
                            '<p><a href="http://' + DISTRIBUTION + '/meeting?eventId=' + str(event_id) + '&passcode=' + str(meeting_passcode) + '">Meeting Link</a></p>'
                        ),
                        'Charset': 'UTF-8'
                        }
                    }
                },
        )
    except Exception as error:
        logger.error('%s SES SendEmail Error: %s', LOG_PREFIX, error)
        raise error
