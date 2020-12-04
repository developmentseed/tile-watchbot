"""Process."""

import importlib
import json
import logging
import os
import warnings
from enum import Enum
from io import BytesIO
from types import DynamicClassAttribute
from typing import Any, BinaryIO, Dict, Optional, Union
from urllib.parse import urlparse

import numpy
from boto3.session import Session as boto3_session
from cogeo_mosaic.backends import MosaicBackend
from cogeo_mosaic.errors import NoAssetFoundError
from morecantile import Tile
from pydantic import BaseModel, validator
from rio_tiler.errors import EmptyMosaicError, TileOutsideBounds
from rio_tiler.io import BaseReader
from rio_tiler.mosaic.methods import defaults

from .settings import mosaic_config

logger = logging.getLogger("tilebot")


class PixelSelectionMethod(str, Enum):
    """rio-tiler-mosaic pixel selection methods"""

    first = "first"
    highest = "highest"
    lowest = "lowest"
    mean = "mean"
    median = "median"
    stdev = "stdev"

    @DynamicClassAttribute
    def method(self):
        """Return rio-tiler-mosaic pixel selection class"""
        return getattr(defaults, f"{self._value_.title()}Method")


def _s3_upload(
    file_obj: BinaryIO, bucket: str, key: str, client: boto3_session.client = None
) -> bool:
    if not client:
        session = boto3_session()
        client = session.client("s3")
    client.upload_fileobj(file_obj, bucket, key)
    return True


def _get_options(self, src_dst, indexes: Optional[str] = None):
    """Create Reader options."""
    kwargs: Dict[str, Any] = {}

    assets = getattr(src_dst, "assets", None)
    bands = getattr(src_dst, "bands", None)

    if indexes:
        if assets:
            kwargs["assets"] = indexes.split(",")
        elif bands:
            kwargs["bands"] = indexes.split(",")
        else:
            kwargs["indexes"] = tuple(int(s) for s in indexes.split(","))
    else:
        if assets:
            kwargs["assets"] = assets
        if bands:
            kwargs["bands"] = bands

    return kwargs


class Message(BaseModel):
    """Pydantic model for message."""

    tile: Union[str, Tile]
    dataset: str
    indexes: Optional[str]  # 1,2,3 or asset1,asset2,asset3 or B1,B2,B3
    expression: Optional[str]
    pixel_selection: Optional[PixelSelectionMethod]
    reader: str = "rio_tiler.io.COGReader"

    @validator("tile")
    def validate_and_parse(cls, v) -> Tile:
        """Parse and return Morecantile Tile."""
        z, x, y = list(map(int, v.split("-")))
        return Tile(x, y, z)

    class Config:
        """Config for model."""

        extra = "ignore"


def process(message):
    """Create NPY tile."""
    out_bucket = os.environ["OUTPUT_BUCKET"]

    # Parse SNS message
    if isinstance(message, str):
        message = json.loads(message)
    message = Message(**message)

    # Import Reader Class
    module, classname = message.reader.rsplit(".", 1)
    reader = getattr(importlib.import_module(module), classname)  # noqa
    if not issubclass(reader, BaseReader):
        warnings.warn("Reader should be a subclass of rio_tiler.io.BaseReader")

    kwargs: Dict[str, Any] = {}
    if message.expression:
        kwargs["expression"] = message.expression
    if message.pixel_selection:
        kwargs["pixel_selection"] = message.pixel_selection.method

    # We allow multiple datasets in form of `dataset1,dataset2,dataset3`
    for dataset in message.dataset.split(","):
        # MosaicReader
        # mosaic+mosaicid://
        # mosaic+https://
        # mosaic+s3://
        parsed = urlparse(dataset)
        if parsed.scheme and (
            parsed.scheme.startswith("mosaic+") or parsed.scheme == "mosaicid"
        ):
            mosaic_dataset = dataset.replace("mosaic+", "")

            if mosaic_dataset.startswith("mosaicid://"):  # dataset is a mosaic id
                bname = mosaic_dataset.replace("mosaicid://", "")
                if mosaic_config.backend == "dynamodb://":
                    url = f"{mosaic_config.backend}{mosaic_config.host}:{bname}"
                else:
                    url = f"{mosaic_config.backend}{mosaic_config.host}/{bname}{mosaic_config.format}"

            else:  # dataset is a full mosaic path
                url = mosaic_dataset
                bname = os.path.basename(mosaic_dataset).split(".")[0]

            out_key = os.path.join(
                bname, f"{message.tile.z}-{message.tile.x}-{message.tile.y}.npz"
            )
            with MosaicBackend(url, reader=reader) as src_dst:
                if not message.expression:
                    # For Mosaic we cannot guess the assets or bands
                    # User will have to pass indexes=B1,B2,B3 or indexes=asset1,asset2
                    bidx_kwargs = _get_options(src_dst, message.indexes)
                    kwargs = {**kwargs, **bidx_kwargs}

                try:
                    data, _ = src_dst.tile(*message.tile, **kwargs)
                except (NoAssetFoundError, EmptyMosaicError):
                    logger.warning(
                        f"No data of {mosaic_dataset} - {message.tile.z}-{message.tile.x}-{message.tile.y}"
                    )
                    continue

        # BaseReader
        else:
            bname = os.path.basename(dataset).split(".")[0]
            out_key = os.path.join(
                bname, f"{message.tile.z}-{message.tile.x}-{message.tile.y}.npz"
            )
            with reader(dataset) as src_dst:
                if not message.expression:
                    bidx_kwargs = _get_options(src_dst, message.indexes)
                    kwargs = {**kwargs, **bidx_kwargs}
                try:
                    data = src_dst.tile(*message.tile, **kwargs)
                except TileOutsideBounds:
                    continue

        bio = BytesIO()
        numpy.savez_compressed(bio, data=data.data, mask=data.mask)
        bio.seek(0)
        _s3_upload(bio, out_bucket, out_key)

    return True
