"""tilebot main cmd."""

import json
import logging
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError

from tilebot.process import process

logger = logging.getLogger("tilebot")
logging.getLogger("botocore.credentials").disabled = True
logging.getLogger("botocore.utils").disabled = True
logging.getLogger("rio-tiler").setLevel(logging.ERROR)


def _parse_message(message):
    if message.get("Records"):
        record = message["Records"][0]
        message = json.loads(record["body"])
    return message["Message"]


def main():
    """Pull Message and Process."""
    region_name = os.environ["REGION"]
    queue_name = os.environ["QUEUE_NAME"]

    sqs = boto3.resource("sqs", region_name=region_name)

    # Get the queue
    try:
        queue = sqs.get_queue_by_name(QueueName=queue_name)
    except ClientError:
        logger.warning(f"SQS Queue '{queue_name}' ({region_name}) not found")
        sys.exit(1)

    while True:
        message = False
        for message in queue.receive_messages():
            m = _parse_message(json.loads(message.body))
            logger.debug(m)
            process(m)

            # Let the queue know that the message is processed
            message.delete()

        if not message:
            logger.warning("No message in Queue, will sleep for 60 seconds...")
            time.sleep(60)  # if no message, let's wait 60secs


if __name__ == "__main__":
    main()
