"""Worker."""

import json
import logging

from .process import process

logger = logging.getLogger("tilebot")
logging.getLogger("botocore.credentials").disabled = True
logging.getLogger("botocore.utils").disabled = True
logging.getLogger("rio-tiler").setLevel(logging.ERROR)


def _parse_message(message):
    if not message.get("Records"):
        return message

    record = message["Records"][0]
    body = json.loads(record["body"])
    return body["Message"]


def main(event, context):
    """
    Handle events.

    Events:
        - SQS queue

    """
    message = _parse_message(event)
    logger.info(message)
    return process(message)
