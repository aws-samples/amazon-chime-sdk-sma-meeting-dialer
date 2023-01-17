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

# Set LogLevel using environment variable, fallback to INFO if not present
logger = logging.getLogger()
try:
    LOG_LEVEL = os.environ['LogLevel']
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
    event_type = event['InvocationEventType']
    transaction_id = event['CallDetails']['TransactionId']
    transaction_attributes = event['CallDetails'].get('TransactionAttributes')
    if transaction_attributes is None:
        transaction_attributes = {}
    participants = event['CallDetails']['Participants']
    call_id = participants[0]['CallId']

    global LOG_PREFIX
    LOG_PREFIX = f'TransactionId: {event_type} {transaction_id}'
    logger.info('RECV %s \nEvent: %s', LOG_PREFIX, json.dumps(event, indent=4))

    if event_type == 'NEW_INBOUND_CALL':
        transaction_attributes['call_type'] = 'inbound'
        return response(inbound_call_speak_and_get_digits_action("<speak>Please enter your 6 digit event i d</speak>"), transaction_attributes=transaction_attributes)
    elif event_type == 'HANGUP':
        # if transaction_attributes.get('delete_attendee') != 'false' and transaction_attributes.get('meeting_id') is not None:
        #     logger.info('Deleting attendee %s in meeting %s', transaction_attributes['attendee_id'],  transaction_attributes['meeting_id'])
        #     chime_sdk_meeting_client.delete_attendee(MeetingId=transaction_attributes['meeting_id'], AttendeeId=transaction_attributes['attendee_id'])
        # current_attendee_list = chime_sdk_meeting_client.list_attendees(MeetingId=transaction_attributes['meeting_id'])
        # logger.info('Current Attendee List: %s', json.dumps(current_attendee_list['Attendees']))
        # if len(current_attendee_list['Attendees']) == 0:
        #     logger.info('No more attendees, deleting meeting: %s', transaction_attributes['meeting_id'])
        #     chime_sdk_meeting_client.delete_meeting(MeetingId=transaction_attributes['meeting_id'])
        return response(transaction_attributes=transaction_attributes)
    elif event_type == 'NEW_OUTBOUND_CALL':
        logger.info('Adding transaction attributes')
        transaction_attributes['meeting_id'] = event['ActionData']['Parameters']['Arguments']['meeting_id']
        transaction_attributes['attendee_id'] = event['ActionData']['Parameters']['Arguments']['attendee_id']
        transaction_attributes['join_token'] = event['ActionData']['Parameters']['Arguments']['join_token']
        transaction_attributes['event_id'] = event['ActionData']['Parameters']['Arguments']['event_id']
        transaction_attributes['meeting_passcode'] = event['ActionData']['Parameters']['Arguments']['meeting_passcode']
        transaction_attributes['call_type'] = 'outbound'
        return response(transaction_attributes=transaction_attributes)
    elif event_type == 'CALL_ANSWERED':
        return response(outbound_call_speak_and_get_digits_action(transaction_attributes), transaction_attributes=transaction_attributes)
    elif event_type == 'ACTION_SUCCESSFUL':
        if event['ActionData']['Type'] == 'SpeakAndGetDigits':
            if transaction_attributes['call_type'] == 'outbound':
                received_digits = event['ActionData']['ReceivedDigits']
                if received_digits == '1':
                    return response(join_chime_meeting_action(call_id, transaction_attributes), transaction_attributes=transaction_attributes)
                else:
                    # transaction_attributes['delete_attendee'] = 'false'
                    return response(speak_action(call_id, "Disconnecting you."), hangup_action(call_id), transaction_attributes=transaction_attributes)
            elif transaction_attributes['call_type'] == 'inbound':
                received_digits = event['ActionData']['ReceivedDigits']
                if 'event_id' not in transaction_attributes:
                    transaction_attributes['event_id'] = received_digits
                    return response(
                        inbound_call_speak_and_get_digits_action("<speak>Please enter your 6 digit passcode to join the meeting.</speak>"),
                        transaction_attributes=transaction_attributes)
                else:
                    try:
                        meeting_info = meeting_table.get_item(Key={"EventId": transaction_attributes['event_id'], 'MeetingPasscode': received_digits})
                        logger.info('Meeting info: %s', json.dumps(meeting_info,  cls=DecimalEncoder, indent=4))
                    except Exception as error:
                        logger.error('Error getting meeting info from DynamoDB: %s', error)
                        raise error
                    if meeting_info.get('Item'):
                        transaction_attributes['meeting_id'] = meeting_info['Item']['MeetingId']
                        transaction_attributes['attendee_id'] = meeting_info['Item']['AttendeeId']
                        transaction_attributes['join_token'] = meeting_info['Item']['JoinToken']
                        transaction_attributes['event_id'] = str(meeting_info['Item']['EventId'])
                        transaction_attributes['meeting_passcode'] = received_digits
                        return response(join_chime_meeting_action(call_id, transaction_attributes), transaction_attributes=transaction_attributes)
                    else:
                        return response(speak_action(call_id, "Invalid meeting passcode."), hangup_action(call_id), transaction_attributes=transaction_attributes)
        if event['ActionData']['Type'] == 'JoinChimeMeeting':
            update_response = meeting_table.update_item(
                Key={"EventId": transaction_attributes['event_id'], "MeetingPasscode": transaction_attributes['meeting_passcode']},
                UpdateExpression="set JoinMethod = :j",
                ExpressionAttributeValues={":j": 'Phone'},
                ReturnValues="UPDATED_NEW"),
            logger.info('Update response: %s', json.dumps(update_response, indent=4))
            return response(speak_action(call_id, "You have been joined to the meeting."), transaction_attributes=transaction_attributes)
        else:
            return response(transaction_attributes=transaction_attributes)
    elif event_type == 'ACTION_FAILED':
        if event['ActionData']['Type'] == 'JoinChimeMeeting':
            return response(speak_action(call_id, "Sorry, I could not connect you to the meeting"), hangup_action(call_id), transaction_attributes=transaction_attributes)
        if event['ActionData']['Type'] == 'SpeakAndGetDigits':
            if event['ActionData']['ErrorType'] == 'InvalidDigitsReceived':
                # transaction_attributes['delete_attendee'] = 'false'
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

    logger.info('RESPONSE %s \n %s', LOG_PREFIX, json.dumps(res, indent=4))
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
