"""app settings"""

import pydantic
from typing import Optional


class MosaicSettings(pydantic.BaseSettings):
    """Application settings"""

    backend: Optional[str]
    host: Optional[str]
    format: Optional[str] = ".json"

    class Config:
        """model config"""

        env_prefix = "MOSAIC_"


mosaic_config = MosaicSettings()
