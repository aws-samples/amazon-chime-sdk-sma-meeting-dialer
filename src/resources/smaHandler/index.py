import os
import decimal
import json
import logging
import boto3
import botocore.exceptions

chime_sdk_meeting_client = boto3.client('chime-sdk-meetings')
dynamo_client = boto3.resource('dynamodb')

MEETING_TABLE = os.environ['MEETING_TABLE']

meeting_table = dynamo_client.Table(MEETING_TABLE)

# Set LOG_LEVEL using environment variable, fallback to INFO if not present
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


def handler(event, context):
    event_type = event['InvocationEventType']
    transaction_id = event['CallDetails']['TransactionId']
    transaction_attributes = event['CallDetails'].get('TransactionAttributes')
    if transaction_attributes is None:
        transaction_attributes = {}
    participants = event['CallDetails']['Participants']
    call_id = participants[0]['CallId']

    global LOG_PREFIX
    LOG_PREFIX = f'SMA Handler: '
    logger.info('%s RECV Event: %s', LOG_PREFIX, json.dumps(event, indent=4))

    if event_type == 'NEW_INBOUND_CALL':
        transaction_attributes['call_type'] = 'inbound'
        return response(inbound_call_speak_and_get_digits_action("<speak>Please enter your 6 digit event i d</speak>"), transaction_attributes=transaction_attributes)
    elif event_type == 'HANGUP':
        if participants[0]['To'] == '+17035550122':
            return response(hangup_action(participants[1]['CallId']), transaction_attributes=transaction_attributes)
        elif len(participants) == 2:
            logger.info('%s Deleting attendee %s in meeting %s', LOG_PREFIX, transaction_attributes['attendee_id'],  transaction_attributes['meeting_id'])
            chime_sdk_meeting_client.delete_attendee(MeetingId=transaction_attributes['meeting_id'], AttendeeId=transaction_attributes['attendee_id'])
            current_attendee_list = chime_sdk_meeting_client.list_attendees(MeetingId=transaction_attributes['meeting_id'])
            logger.info('Current Attendee List: %s', json.dumps(current_attendee_list['Attendees']))
            if len(current_attendee_list['Attendees']) == 0:
                logger.info('%s No more attendees, deleting meeting: %s', LOG_PREFIX, transaction_attributes['meeting_id'])
                chime_sdk_meeting_client.delete_meeting(MeetingId=transaction_attributes['meeting_id'])
            return response(transaction_attributes=transaction_attributes)
        else:
            return response(hangup_action(call_id), transaction_attributes=transaction_attributes)
    elif event_type == 'NEW_OUTBOUND_CALL':
        logger.info('%s Adding transaction attributes', LOG_PREFIX)
        transaction_attributes['meeting_id'] = event['ActionData']['Parameters']['Arguments']['meeting_id']
        transaction_attributes['attendee_id'] = event['ActionData']['Parameters']['Arguments']['attendee_id']
        transaction_attributes['join_token'] = event['ActionData']['Parameters']['Arguments']['join_token']
        transaction_attributes['event_id'] = event['ActionData']['Parameters']['Arguments']['event_id']
        transaction_attributes['meeting_passcode'] = event['ActionData']['Parameters']['Arguments']['meeting_passcode']
        transaction_attributes['phone_number'] = event['ActionData']['Parameters']['Arguments']['phone_number']
        transaction_attributes['call_type'] = 'outbound'
        return response(transaction_attributes=transaction_attributes)
    elif event_type == 'CALL_ANSWERED':
        return response(outbound_call_speak_and_get_digits_action(transaction_attributes), transaction_attributes=transaction_attributes)
    elif event_type == 'ACTION_SUCCESSFUL':
        logger.info('%s Action Successful', LOG_PREFIX)
        if event['ActionData']['Type'] == 'SpeakAndGetDigits':
            logger.info('%s SpeakAndGetDigits Action Successful', LOG_PREFIX)
            if transaction_attributes['call_type'] == 'outbound':
                logger.info('%s CallType is outbound', LOG_PREFIX)
                received_digits = event['ActionData']['ReceivedDigits']
                if received_digits == '1':
                    logger.info('%s Received digits is 1', LOG_PREFIX)
                    update_table(transaction_attributes, transaction_attributes['meeting_id'], transaction_attributes['attendee_id'])
                    return response(join_chime_meeting_action(call_id, transaction_attributes), transaction_attributes=transaction_attributes)
                else:
                    logger.info('%s Received digits is not 1', LOG_PREFIX)
                    return response(speak_action(call_id, "Disconnecting you."), hangup_action(call_id), transaction_attributes=transaction_attributes)
            elif transaction_attributes['call_type'] == 'inbound':
                logger.info('%s CallType is inbound', LOG_PREFIX)
                received_digits = event['ActionData']['ReceivedDigits']
                if 'event_id' not in transaction_attributes:
                    logger.info('%s Event Id not in transaction attributes', LOG_PREFIX)
                    transaction_attributes['event_id'] = received_digits
                    return response(
                        inbound_call_speak_and_get_digits_action("<speak>Please enter your 6 digit passcode to join the meeting.</speak>"),
                        transaction_attributes=transaction_attributes)
                else:
                    logger.info('%s Event ID is in transaction attributes', LOG_PREFIX)
                    try:
                        logger.info('%s Getting Item from DynamoDB for Event ID: %s and Passcode: %s', LOG_PREFIX, transaction_attributes['event_id'], received_digits)
                        event_info = meeting_table.get_item(Key={"EventId": transaction_attributes['event_id'], 'MeetingPasscode': received_digits})
                        logger.info('%s Event Info: %s', LOG_PREFIX, json.dumps(event_info,  cls=DecimalEncoder, indent=4))
                    except Exception as error:
                        logger.error('%s DynamoDB Exception: %s', LOG_PREFIX, error)
                        raise error
                    if event_info.get('Item'):
                        logger.info('%s Passcode and Event ID combination is valid', LOG_PREFIX)
                        transaction_attributes['phone_number'] = event_info['Item']['PhoneNumber']
                        transaction_attributes['event_id'] = str(event_info['Item']['EventId'])
                        transaction_attributes['meeting_passcode'] = received_digits
                        transaction_attributes['meeting_id'] = event_info['Item']['MeetingId']
                        meeting_info = create_meeting(transaction_attributes)
                        # transaction_attributes['meeting_id'] = meeting_info['Meeting']['MeetingId']
                        transaction_attributes['attendee_id'] = meeting_info['Attendees'][0]['AttendeeId']
                        transaction_attributes['join_token'] = meeting_info['Attendees'][0]['JoinToken']
                        return response(join_chime_meeting_action(call_id, transaction_attributes), transaction_attributes=transaction_attributes)
                    else:
                        logger.info('%s Passcode and Event ID combination is not valid', LOG_PREFIX)
                        return response(speak_action(call_id, "Invalid meeting passcode."), hangup_action(call_id), transaction_attributes=transaction_attributes)
        if event['ActionData']['Type'] == 'JoinChimeMeeting':
            logger.info('%s JoinChimeMeetingAction Successful', LOG_PREFIX)
            return response(speak_action(call_id, "You have been joined to the meeting."), transaction_attributes=transaction_attributes)
        else:
            logger.info('%s Action Type is not SpeakAndGetDigits or JoinChimeMeeting', LOG_PREFIX)
            return response(transaction_attributes=transaction_attributes)
    elif event_type == 'ACTION_FAILED':
        logger.info('%s Action Failed', LOG_PREFIX)
        if event['ActionData']['Type'] == 'JoinChimeMeeting':
            logger.info('%s JoinChimeMeetingAction Failed', LOG_PREFIX)
            return response(speak_action(call_id, "Sorry, I could not connect you to the meeting"), hangup_action(call_id), transaction_attributes=transaction_attributes)
        if event['ActionData']['Type'] == 'SpeakAndGetDigits':
            logger.info('%s SpeakAndGetDigits Failed', LOG_PREFIX)
            if event['ActionData']['ErrorType'] == 'InvalidDigitsReceived':
                logger.info('%s InvalidDigitsReceived', LOG_PREFIX)
                return response(hangup_action(call_id), transaction_attributes=transaction_attributes)
        else:
            return response(transaction_attributes=transaction_attributes)
    else:
        return response(transaction_attributes=transaction_attributes)


def response(*actions, transaction_attributes):
    res = {
        'SchemaVersion': '1.0',
        'Actions': [*actions],
        'TransactionAttributes': transaction_attributes
    }

    logger.info('%s RESPONSE %s', LOG_PREFIX, json.dumps(res, indent=4))
    return res


def outbound_call_speak_and_get_digits_action(transaction_attributes):
    return {
        "Type": "SpeakAndGetDigits",
        "Parameters": {
            "MinNumberOfDigits": 1,
            "MaxNumberOfDigits": 1,
            "Repeat": 3,
            "RepeatDurationInMilliseconds": 3000,
            "InputDigitsRegex": "[1-2]",
            "InBetweenDigitsDurationInMilliseconds": 1000,
            "TerminatorDigits": ["#"],
            "SpeechParameters": {
                "Text": "<speak>You are needed on a call for event <say-as interpret-as='digits'>" +
                transaction_attributes['event_id'] +
                "</say-as>. Press 1 to join, 2 to decline.</speak>",
                "Engine": "neural",
                "LanguageCode": "en-US",
                "TextType": "ssml",
                "VoiceId": "Joanna"},
            "FailureSpeechParameters": {
                "Text": "Sorry, I didn't get that.  Please press 1 to join, 2 to decline.",
                "Engine": "neural",
                "LanguageCode": "en-US",
                "TextType": "text",
                "VoiceId": "Joanna"},
        },
    }


def inbound_call_speak_and_get_digits_action(text):
    return {
        "Type": "SpeakAndGetDigits",
        "Parameters": {
            "MinNumberOfDigits": 6,
            "MaxNumberOfDigits": 6,
            "Repeat": 3,
            "RepeatDurationInMilliseconds": 7500,
            "InputDigitsRegex": "[0-9]",
            "InBetweenDigitsDurationInMilliseconds": 1000,
            "TerminatorDigits": ["#"],
            "SpeechParameters": {
                "Text": text,
                "Engine": "neural",
                "LanguageCode": "en-US",
                "TextType": "ssml",
                "VoiceId": "Joanna"},
            "FailureSpeechParameters": {
                "Text": "Sorry, I didn't get that.  Please try again.",
                "Engine": "neural",
                "LanguageCode": "en-US",
                "TextType": "text",
                "VoiceId": "Joanna"},
        },
    }


def speak_action(call_id, message):
    return {
        "Type": "Speak",
        "Parameters": {
                "Text": message,
                "CallId": call_id,
                "Engine": "neural",
                "LanguageCode": "en-US",
                "TextType": "text",
                "VoiceId": "Joanna"
        }
    }


def hangup_action(call_id):
    return {
        'Type': 'Hangup',
        'Parameters': {
                "CallId": call_id,
                'SipResponseCode': '0'
        }
    }


def join_chime_meeting_action(call_id, transaction_attributes):
    return {
        'Type': 'JoinChimeMeeting',
        'Parameters': {
                "JoinToken": transaction_attributes['join_token'],
                "CallId": call_id,
                "MeetingId": transaction_attributes['meeting_id']
        }
    }


def create_meeting(transaction_attributes):
    logger.info('%s Creating meeting for event %s', LOG_PREFIX, transaction_attributes['event_id'])

    check_attendee(transaction_attributes)

    try:
        meeting_info = chime_sdk_meeting_client.create_meeting_with_attendees(
            ClientRequestToken=transaction_attributes['event_id'],
            MediaRegion='us-east-1',
            ExternalMeetingId=transaction_attributes['event_id'],
            Attendees=[{
                'ExternalUserId': transaction_attributes['phone_number']
            }]
        )
        update_table(transaction_attributes,  meeting_info['Meeting']['MeetingId'], meeting_info['Attendees'][0]['AttendeeId'])
        logger.info('%s Meeting created: %s', LOG_PREFIX, meeting_info)
        return meeting_info
    except Exception as error:
        logger.error('%s Error creating meeting: %s', LOG_PREFIX, error)
        return error


def check_attendee(transaction_attributes):
    logger.info('%s Getting attendee list for meeting %s', LOG_PREFIX, transaction_attributes['meeting_id'])
    try:
        attendee_info = chime_sdk_meeting_client.list_attendees(
            MeetingId=transaction_attributes['meeting_id'],
        )
        for attendee in attendee_info['Attendees']:
            if attendee['ExternalUserId'] == transaction_attributes['phone_number']:
                logger.info('%s Attendee already exists', LOG_PREFIX)
                delete_attendee(transaction_attributes['meeting_id'],  attendee['AttendeeId'])
            else:
                continue
        return True
    except Exception as error:
        logger.error('%s Error getting attendee: %s', LOG_PREFIX, error)
        return error


def delete_attendee(meeting_id, attendee_id):
    logger.info('%s Deleting attendee %s for meeting %s', LOG_PREFIX, attendee_id, meeting_id)
    try:
        chime_sdk_meeting_client.delete_attendee(
            MeetingId=meeting_id,
            AttendeeId=attendee_id
        )
        logger.info('%s Attendee deleted', LOG_PREFIX)
        return True
    except Exception as error:
        logger.error('%s Error deleting attendee: %s', LOG_PREFIX, error)
        return error


def update_table(transaction_attributes, meeting_id, attendee_id):
    logger.info('%s Updating table for event %s', LOG_PREFIX, transaction_attributes['event_id'])
    try:
        table_update = meeting_table.update_item(
                    Key={"EventId": transaction_attributes['event_id'], "MeetingPasscode": transaction_attributes['meeting_passcode']},
                    UpdateExpression="set JoinMethod = :j, MeetingId = :m, AttendeeId = :a",
                    ExpressionAttributeValues={":j": 'Phone',  ":m": meeting_id, ":a": attendee_id},
                    ReturnValues="UPDATED_NEW"),
        logger.info('%s s Table update: %s', LOG_PREFIX, json.dumps(table_update, cls=DecimalEncoder, indent=4))
        return True
    except Exception as error:
        logger.error('%s Error updating table: %s', LOG_PREFIX, error)
        return error
