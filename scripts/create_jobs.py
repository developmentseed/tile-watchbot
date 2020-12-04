"""create_job: Feed SQS queue."""

import json
from concurrent import futures
from functools import partial

import click
from boto3.session import Session as boto3_session
from rio_tiler.utils import _chunks


def aws_send_message(message, topic, client=None):
    """Send SNS message."""
    if not client:
        session = boto3_session()
        client = session.client("sns")
    return client.publish(Message=json.dumps(message), TargetArn=topic)


def sns_worker(messages, topic, subject=None):
    """Send batch of SNS messages."""
    session = boto3_session(region_name="us-west-2")
    client = session.client("sns")
    for message in messages:
        aws_send_message(message, topic, client=client)
    return True


@click.command()
@click.argument("tiles", default="-", type=click.File("r"))
@click.option("--dataset", type=str, required=True)
@click.option("--reader", type=str)
@click.option("--layers", type=str)
@click.option("--expression", type=str)
@click.option("--pixel-selection", type=str)
@click.option("--topic", type=str, required=True, help="SNS Topic")
def cli(tiles, dataset, reader, layers, expression, pixel_selection, topic):
    """
    Example:
    cat LaMyViet.geojson| supermercado burn 14 | xt -d'-' > list_z14.txt

    cat list.txt | python -m create_jobs - \
        --dataset mosaicid://mydataset \
        --expression "B02,B8A,B11,B12,(B08 - B04) / (B08 + B04),1.5 * (B08-B04) / (0.5 + B08 + B04)" \
        --topic arn:aws:sns:us-west-2:1111111111:tilebot-lambda-production-TopicAAAAAAAAAAAAAAAAAA

    """

    def _create_message(tile):
        m = {"tile": tile.rstrip(), "dataset": dataset}
        if layers:
            m.update({"indexes": layers})
        if expression:
            m.update({"expression": expression})
        if reader:
            m.update({"reader": reader})
        if pixel_selection:
            m.update({"pixel_selection": pixel_selection})

        return m

    messages = [_create_message(tile) for tile in tiles]

    parts = _chunks(messages, 50)
    _send_message = partial(sns_worker, topic=topic)
    with futures.ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(_send_message, parts)


if __name__ == "__main__":
    cli()
