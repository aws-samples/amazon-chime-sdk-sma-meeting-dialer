import logging
import json
import decimal
import os

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
    global LOG_PREFIX
    LOG_PREFIX = 'EventBridge Notification: '
    
    if 'detail-type' in event:
        if event['detail-type'] == 'AWS API Call via CloudTrail':
            logger.info('%s Event Name: %s | Event Source: %s', LOG_PREFIX, event['detail']['eventName'], event['detail']['eventSource'])
            logger.debug('%s userIdentity: %s', LOG_PREFIX, json.dumps(event['detail']['userIdentity'],  cls=DecimalEncoder, indent=4))
            logger.debug('%s requestParameters: %s', LOG_PREFIX, json.dumps(event['detail']['requestParameters'],  cls=DecimalEncoder, indent=4))
            logger.debug('%s responseElements: %s', LOG_PREFIX, json.dumps(event['detail']['responseElements'],  cls=DecimalEncoder, indent=4))
        else:
            logger.info('%s Detail Type: %s | Event Type: %s', LOG_PREFIX, event['detail-type'], event['detail']['eventType'])
            logger.debug('%s  %s', LOG_PREFIX, json.dumps(event,  cls=DecimalEncoder, indent=4))