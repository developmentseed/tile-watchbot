"""create_job: Feed SQS queue."""

import json
from functools import partial
from concurrent import futures
from collections import Counter

import click

from boto3.session import Session as boto3_session

from rio_tiler.utils import _chunks


def sources_callback(ctx, param, value):
    """Validate uniqueness of sources."""
    sources = list([name.strip() for name in value])

    # Identify duplicate sources.
    dupes = [name for (name, count) in Counter(sources).items() if count > 1]
    if len(dupes) > 0:
        raise click.BadParameter(
            "Duplicated sources {!r} cannot be processed.".format(dupes)
        )

    return sources


def aws_send_message(message, topic, client=None):
    """Send SNS message."""
    if not client:
        session = boto3_session()
        client = session.client('sns')
    return client.publish(Message=json.dumps(message), TargetArn=topic)


def sns_worker(messages, topic, subject=None):
    """Send batch of SNS messages."""
    session = boto3_session(region_name="us-west-2")
    client = session.client('sns')
    for message in messages:
        aws_send_message(message, topic, client=client)
    return True


@click.command()
@click.argument("sources", default="-", type=click.File("r"), callback=sources_callback)
@click.option("--layer", type=str, required=True)
@click.option("--expression", type=str)
@click.option(
    "--topic",
    type=str,
    required=True,
    help="SNS Topic",
)
def cli(
    sources,
    layer,
    expression,
    topic
):
    """
    Example:
    cat LaMyViet.geojson| supermercado burn 14 | xt -d'-' > list_z14.txt
    cat list.txt | python -m create_jobs - \
        --layer cccmc.sentinel2_winter2018 \
        --topic arn:aws:sns:us-west-2:552819999234:tilebot-lambda-production-TopicBFC7AF6E-1CNDRSH5TB850

    """

    def _create_message(tile):
        m = {"tile": tile, "layer": layer}
        if expression:
            m["expression"] = expression
        return m

    messages = [_create_message(source) for source in sources]

    parts = _chunks(messages, 50)
    _send_message = partial(sns_worker, topic=topic)
    with futures.ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(_send_message, parts)


if __name__ == "__main__":
    cli()
