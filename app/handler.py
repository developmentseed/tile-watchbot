"""Worker."""

from typing import BinaryIO

import os
from io import BytesIO
import json

from boto3.session import Session as boto3_session

from cogeo_mosaic.backends import MosaicBackend
from cogeo_mosaic.errors import NoAssetFoundError
from rio_tiler_pds.sentinel.aws import S2COGReader
from rio_tiler.mosaic.methods.defaults import MedianMethod
from rio_tiler.utils import render

from app.settings import mosaic_config


def _s3_upload(
    file_obj: BinaryIO, bucket: str, key: str, client: boto3_session.client = None
) -> bool:
    if not client:
        session = boto3_session()
        client = session.client("s3")
    client.upload_fileobj(file_obj, bucket, key)
    return True


def process(message):
    """Create NPY tile."""
    if isinstance(message, str):
        message = json.loads(message)

    tile = message["tile"]
    layer = message["layer"]
    expression = message.get(
        "expression",
        "B02,B8A,B11,B12,(B08 - B04) / (B08 + B04),1.5 * (B08-B04) / (0.5 + B08 + B04)",
    )

    out_bucket = os.environ["OUTPUT_BUCKET"]
    out_key = os.path.join(layer, f"{tile}.npy")

    url = f"{mosaic_config.backend}{mosaic_config.host}:{layer}"
    z, x, y = list(map(int, tile.split("-")))

    with MosaicBackend(url, reader=S2COGReader) as src_dst:
        try:
            (data, _), _ = src_dst.tile(
                x,
                y,
                z,
                pixel_selection=MedianMethod(),
                expression=expression
            )
        except NoAssetFoundError:
            return True

        if data is None:
            return True

        img = BytesIO(render(data, img_format="NPY"))
        _s3_upload(img, out_bucket, out_key)

    return True


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
