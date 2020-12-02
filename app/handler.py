"""Worker."""

import json

from .process import process


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
    return process(message)
