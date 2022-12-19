import os
import json
import logging
import boto3
from botocore.exceptions import ClientError

# Set LogLevel using environment variable, fallback to INFO if not present
logger = logging.getLogger()
try:
    log_level = os.environ['LogLevel']
    if log_level not in ['INFO', 'DEBUG']:
        log_level = 'INFO'
except BaseException:
    log_level = 'INFO'
logger.setLevel(log_level)


def handler(event, context):
    event_type = event['InvocationEventType']
    transaction_id = event['CallDetails']['TransactionId']
    transaction_attributes = event['CallDetails'].get('TransactionAttributes')
    participants = event['CallDetails']['Participants']
    call_id = participants[0]['CallId']

    global log_prefix
    log_prefix = f'TransactionId: {transaction_id} {event_type}'
    logger.info('RECV {%s} Event: {%s}', log_prefix, json.dumps(event))

    if event_type == 'NEW_INBOUND_CALL':
        return response(transaction_attributes=transaction_attributes)
    elif event_type == 'HANGUP':
        return response(transaction_attributes=transaction_attributes)
    elif event_type == 'NEW_OUTBOUND_CALL':
        transaction_attributes['meeting_id'] = event['ActionData']['Parameters']['Arguments']['meeting_id']
        transaction_attributes['attendee_id'] = event['ActionData']['Parameters']['Arguments']['attendee_id']
        transaction_attributes['join_token'] = event['ActionData']['Parameters']['Arguments']['join_token']
        transaction_attributes['event_id'] = event['ActionData']['Parameters']['Arguments']['event_id']
        return response(transaction_attributes=transaction_attributes)
    elif event_type == 'CALL_ANSWERED':
        return response(speak_and_get_digits_action(transaction_attributes), transaction_attributes=transaction_attributes)
    elif event_type == 'ACTION_SUCCESSFUL':
        if event['ActionData']['Type'] == 'SpeakAndGetDigits':
            received_digits = event['ActionData']['ReceivedDigits']
            if received_digits == '1':
                return response(join_chime_meeting_action(call_id, transaction_attributes), transaction_attributes=transaction_attributes)
            else:
                return response(speak_action(call_id, "Disconnecting you."), hangup_action(call_id), transaction_attributes=transaction_attributes)
        if event['ActionData']['Type'] == 'JoinChimeMeeting':
            return response(speak_action(call_id, "Joined the meeting."), transaction_attributes=transaction_attributes)


def response(*actions, transaction_attributes):
    res = {
        'SchemaVersion': '1.0',
        'Actions': [*actions],
        'TransactionAttributes': transaction_attributes

    }

    logger.info('RESPONSE {%s} {%s}', log_prefix, json.dumps(res))
    return res


def speak_and_get_digits_action(transaction_attributes):
    return {
        "Type": "SpeakAndGetDigits",
        "Parameters": {
                "MinNumberOfDigits": 1,
                "MaxNumberOfDigits": 1,
                "Repeat": 3,
                "RepeatDurationInMilliseconds": 2000,
                "InputDigitsRegex": "[1-2]",
                "InBetweenDigitsDurationInMilliseconds": 1000,
                "TerminatorDigits": ["#"],
            "SpeechParameters": {
                    "Text": "You are needed on a call for event " + transaction_attributes['event_id'] + ". Press 1 to join, 2 to decline.",
                    "Engine": "neural",
                    "LanguageCode": "en-US",
                    "TextType": "text",
                    "VoiceId": "Joanna"},
            "FailureSpeechParameters": {
                    "Text": "Sorry, I didn't get that.  Please press 1 to join, 2 to decline.",
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
