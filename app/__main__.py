"""goes16 main cmd."""

import json
import logging
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError

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


def main():
    """Pull Message and Process."""
    REGION = os.environ["REGION"]
    sqs = boto3.resource("sqs", region_name=REGION)

    # Get the queue
    try:
        queue = sqs.get_queue_by_name(QueueName=os.environ["QUEUE_NAME"])
    except ClientError:
        print("SQS Queue ot found")
        sys.exit(1)

    while True:
        message = False
        for message in queue.receive_messages():
            m = _parse_message(json.loads(message.body))
            logger.info(m)
            process(m)

            # Let the queue know that the message is processed
            message.delete()

        if not message:
            time.sleep(30)  # if no message, let's wait 30secs

        time.sleep(1)


if __name__ == "__main__":
    main()
