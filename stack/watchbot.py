"""cdk_watchbot.lambdaStack: SQS + SNS + LAMBDA/ECS."""

from typing import Any, Dict, Optional, List

from aws_cdk import (
    core,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecs_patterns,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as sns_sub,
    aws_iam as iam,
    aws_lambda,
    aws_lambda_event_sources,
    aws_ecr_assets,
)


class Lambda(core.Stack):
    """Lambda Watchbot Stack."""

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        handler: str,
        memory: int = 3008,
        timeout: int = 900,
        concurrent: int = 10,
        retry: int = 0,
        permissions: Optional[List[iam.PolicyStatement]] = None,
        environment: Dict = {},
        code_dir: str = "./",
        **kwargs: Any,
    ) -> None:
        """Create AWS Lambda watchbot stack. """
        super().__init__(scope, id, **kwargs)

        permissions = permissions or []

        topic = sns.Topic(self, "lambdaTopic", display_name="Lambda Watchbot SNS Topic")
        dlqueue = sqs.Queue(self, "lambdaDeadLetterQueue")
        queue = sqs.Queue(
            self,
            "lambdaQueue",
            visibility_timeout=core.Duration.seconds(timeout),
            dead_letter_queue=sqs.DeadLetterQueue(queue=dlqueue, max_receive_count=3),
        )

        topic.add_subscription(sns_sub.SqsSubscription(queue))

        asset = aws_lambda.AssetImageCode(directory="./", cmd=[handler])

        worker = aws_lambda.Function(
            self,
            f"{id}-lambda",
            description="Watchbot's worker",
            code=asset,
            handler=aws_lambda.Handler.FROM_IMAGE,
            runtime=aws_lambda.Runtime.FROM_IMAGE,
            memory_size=memory,
            reserved_concurrent_executions=concurrent,
            timeout=core.Duration.seconds(timeout),
            retry_attempts=retry,
            environment=environment,
        )

        for perm in permissions:
            worker.add_to_role_policy(perm)

        worker.add_event_source(
            aws_lambda_event_sources.SqsEventSource(queue, batch_size=1)
        )
        topic.grant_publish(worker)

    # def create_package(self, code_dir: str) -> aws_lambda.Code:
    #     """Build docker image and create package."""
    #     print("Creating lambda package [running in Docker]...")
    #     client = docker.from_env()

    #     print("Building docker image...")
    #     client.images.build(
    #         path=code_dir,
    #         dockerfile="Dockerfile.lambda",
    #         tag="lambda:latest",
    #         rm=True,
    #     )

    #     print("Copying package.zip ...")
    #     client.containers.run(
    #         image="lambda:latest",
    #         command="/bin/sh -c 'cp /tmp/package.zip /local/package.zip'",
    #         remove=True,
    #         volumes={os.path.abspath(code_dir): {"bind": "/local/", "mode": "rw"}},
    #         user=0,
    #     )

    #     return aws_lambda.Code.asset(os.path.join(code_dir, "package.zip"))


# class ECS(core.Stack):
#     """Titiler ECS Fargate Stack."""

#     def __init__(
#         self,
#         scope: core.Construct,
#         id: str,
#         cpu: Union[int, float] = 256,
#         memory: Union[int, float] = 512,
#         mincount: int = 1,
#         maxcount: int = 50,
#         permissions: Optional[List[iam.PolicyStatement]] = None,
#         vpc_id: Optional[str] = None,
#         vpc_is_default: Optional[bool] = None,
#         environment: dict = {},
#         **kwargs: Any,
#     ) -> None:
#         """Define stack."""
#         super().__init__(scope, id, **kwargs)

#         permissions = permissions or []

#         vpc = ec2.Vpc.from_lookup(self, 'vpc', vpc_id=vpc_id, is_default=vpc_is_default)

#         cluster = ecs.Cluster(self, f"{id}-cluster", vpc=vpc)

#         topic = sns.Topic(self, "ecsTopic", display_name="ECS Watchbot SNS Topic")
#         dlqueue = sqs.Queue(self, "ecsDeadLetterQueue")
#         queue = sqs.Queue(
#             self,
#             "ecsQueue",
#             dead_letter_queue=sqs.DeadLetterQueue(
#                 queue=dlqueue, max_receive_count=3
#             ),
#         )
#         environment.update({"REGION": self.region})

#         topic.add_subscription(sns_sub.SqsSubscription(queue))

#         fargate_service = aws_ecs_patterns.QueueProcessingFargateService(
#             self,
#             f"{id}-ecs",
#             cpu=cpu,
#             memory_limit_mib=memory,
#             image=ecs.ContainerImage.from_asset(
#                 directory='.',
#                 file='Dockerfile.ecs',
#                 exclude=["cdk.out"]
#             ),
#             desired_task_count=mincount,
#             max_scaling_capacity=maxcount,
#             enable_ecs_managed_tags=True,
#             environment=environment,
#             max_receive_count=3,
#             enable_logging=True,
#             queue=queue,
#             cluster=cluster,
#             scaling_steps=[
#                 {"upper": 0, "change": -5},
#                 {"lower": 1, "change": +5},
#             ],
#         )

#         for perm in permissions:
#             fargate_service.task_definition.task_role.add_to_policy(perm)
