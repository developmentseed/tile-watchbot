"""STACK Configs."""

from typing import List, Optional

import pydantic


class StackSettings(pydantic.BaseSettings):
    """Application settings"""

    name: str = "tilebot"
    stage: str = "production"

    owner: Optional[str]
    project: Optional[str]
    client: Optional[str]

    buckets: List = []

    timeout: int = 150
    memory: int = 3008
    max_concurrent: int = 200

    # mosaic
    mosaic_backend: str
    mosaic_host: str
    mosaic_format: Optional[str]

    output_bucket: str

    class Config:
        """model config"""

        env_file = "stack/.env"
        env_prefix = "STACK_"


stack_config = StackSettings()
