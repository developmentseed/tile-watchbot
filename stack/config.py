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

    ############################################################################
    # Lambda
    timeout: int = 150
    memory: int = 3008
    max_concurrent: int = 200

    ############################################################################
    # ECS
    min_ecs_instances: int = 0
    max_ecs_instances: int = 50
    ecs_scaling_step: Optional[int]

    # CPU value      |   Memory value
    # 256 (.25 vCPU) | 0.5 GB, 1 GB, 2 GB
    # 512 (.5 vCPU)  | 1 GB, 2 GB, 3 GB, 4 GB
    # 1024 (1 vCPU)  | 2 GB, 3 GB, 4 GB, 5 GB, 6 GB, 7 GB, 8 GB
    # 2048 (2 vCPU)  | Between 4 GB and 16 GB in 1-GB increments
    # 4096 (4 vCPU)  | Between 8 GB and 30 GB in 1-GB increments
    task_cpu: int = 1024
    task_memory: int = 2048

    vpcId: Optional[str]
    default_vpc: Optional[bool]

    ############################################################################
    # mosaic
    mosaic_backend: str
    mosaic_host: str
    mosaic_format: Optional[str]

    ############################################################################
    # others
    output_bucket: str

    class Config:
        """model config"""

        env_file = "stack/.env"
        env_prefix = "STACK_"

    @pydantic.validator("ecs_scaling_step")
    def validate_step(cls, v, values) -> int:
        """Validate Scaling steps."""
        max_instances = values["max_ecs_instances"]
        if v is not None and (v <= 0 or v > max_instances):
            raise ValueError(f"Scaling Step must be > 0 and < {max_instances}")

        return v or int(max_instances / 10)


stack_config = StackSettings()
