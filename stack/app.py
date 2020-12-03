"""app."""

from aws_cdk import aws_iam as iam
from aws_cdk import core
from config import stack_config
from watchbot import Lambda  # , ECS

env = dict(
    CPL_TMPDIR="/tmp",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    GDAL_CACHEMAX="75%",
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
    GDAL_HTTP_MULTIPLEX="YES",
    GDAL_HTTP_VERSION="2",
    PYTHONWARNINGS="ignore",
    VSI_CACHE="TRUE",
    VSI_CACHE_SIZE="1000000",
)
env.update(
    dict(
        MOSAIC_BACKEND=stack_config.mosaic_backend,
        MOSAIC_HOST=stack_config.mosaic_host,
        OUTPUT_BUCKET=stack_config.output_bucket,
    )
)

app = core.App()

# Tag infrastructure
for key, value in {
    "Project": stack_config.name,
    "Stack": stack_config.stage,
    "Owner": stack_config.owner,
    "Client": stack_config.client,
}.items():
    if value:
        core.Tag.add(app, key, value)


perms = []
if stack_config.buckets:
    perms.append(
        iam.PolicyStatement(
            actions=["s3:*"],
            resources=[f"arn:aws:s3:::{bucket}*" for bucket in stack_config.buckets],
        )
    )

stack = core.Stack()
if stack_config.mosaic_backend == "dynamodb://":
    perms.append(
        iam.PolicyStatement(
            actions=["dynamodb:GetItem", "dynamodb:Scan", "dynamodb:BatchWriteItem"],
            resources=[f"arn:aws:dynamodb:{stack.region}:{stack.account}:table/*"],
        )
    )


Lambda(
    app,
    f"{stack_config.name}-lambda-{stack_config.stage}",
    "app.handler.main",
    memory=stack_config.memory,
    timeout=stack_config.timeout,
    concurrent=stack_config.max_concurrent,
    permissions=perms,
    environment=env,
)

# ECS(
#     app,
#     f"{stack_config.name}-ecs-{stack_config.stage}",
#     entrypoint=['python', '-m', 'app'],
#     cpu=stack_config.task_cpu,
#     memory=stack_config.task_memory,
#     mincount=stack_config.min_ecs_instances,
#     maxcount=stack_config.max_ecs_instances,
#     permissions=perms,
#     vpc_id=stack_config.vpcId,
#     vpc_is_default=stack_config.default_vpc,
#     environment=env,
#     env={
#         'account': os.environ["AWS_ACCOUNT_ID"],
#         'region': os.environ["AWS_REGION"]
#     }
# )

app.synth()
