"""cdk_watchbot.lambdaStack: SQS + SNS + LAMBDA/ECS."""

from typing import Any, Dict, List, Optional, Union

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda, aws_lambda_event_sources
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as sns_sub
from aws_cdk import aws_sqs as sqs
from aws_cdk import core
from aws_cdk.aws_applicationautoscaling import ScalingInterval


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
        core.CfnOutput(
            self,
            "SNSTopic",
            value=topic.topic_arn,
            description="SNS Topic ARN",
            export_name="SNSTopic",
        )

        dlqueue = sqs.Queue(self, "lambdaDeadLetterQueue")
        queue = sqs.Queue(
            self,
            "lambdaQueue",
            visibility_timeout=core.Duration.seconds(timeout),
            dead_letter_queue=sqs.DeadLetterQueue(queue=dlqueue, max_receive_count=3),
        )
        core.CfnOutput(
            self,
            "SQSQueueURL",
            value=queue.queue_url,
            description="SQS URL",
            export_name="SQSQueueURL",
        )

        topic.add_subscription(sns_sub.SqsSubscription(queue))

        asset = aws_lambda.AssetImageCode(directory="./")

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


class ECS(core.Stack):
    """Titiler ECS Fargate Stack."""

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        entrypoint: Optional[List] = None,
        cpu: Union[int, float] = 256,
        memory: Union[int, float] = 512,
        mincount: int = 1,
        maxcount: int = 50,
        permissions: Optional[List[iam.PolicyStatement]] = None,
        vpc_id: Optional[str] = None,
        vpc_is_default: Optional[bool] = None,
        environment: dict = {},
        **kwargs: Any,
    ) -> None:
        """Define stack."""
        super().__init__(scope, id, **kwargs)

        permissions = permissions or []

        vpc = ec2.Vpc.from_lookup(self, "vpc", vpc_id=vpc_id, is_default=vpc_is_default)

        cluster = ecs.Cluster(self, f"{id}-cluster", vpc=vpc)

        topic = sns.Topic(self, "ecsTopic", display_name="ECS Watchbot SNS Topic")
        core.CfnOutput(
            self,
            "SNSTopic",
            value=topic.topic_arn,
            description="SNS Topic ARN",
            export_name=f"{id}-SNSTopic",
        )

        dlqueue = sqs.Queue(self, "ecsDeadLetterQueue")
        core.CfnOutput(
            self,
            "DeadSQSQueueURL",
            value=dlqueue.queue_url,
            description="DeadLetter SQS URL",
            export_name=f"{id}-DeadSQSQueueURL",
        )

        queue = sqs.Queue(
            self,
            "ecsQueue",
            dead_letter_queue=sqs.DeadLetterQueue(queue=dlqueue, max_receive_count=3),
        )
        core.CfnOutput(
            self,
            "SQSQueueURL",
            value=queue.queue_url,
            description="SQS URL",
            export_name=f"{id}-SQSQueueURL",
        )

        environment.update({"REGION": self.region, "QUEUE_NAME": queue.queue_name})

        topic.add_subscription(sns_sub.SqsSubscription(queue))

        # I can't find a way to overwrite the entry point
        image = ecs.ContainerImage.from_asset(directory="./")

        fargate_task_definition = ecs.FargateTaskDefinition(
            self, "FargateTaskDefinition", memory_limit_mib=memory, cpu=cpu
        )
        fargate_task_definition.add_container(
            "FargateContainer",
            image=image,
            entry_point=entrypoint,
            environment=environment,
            logging=ecs.LogDrivers.aws_logs(stream_prefix=id),
        )
        fargate_service = ecs.FargateService(
            self,
            "FargateService",
            cluster=cluster,
            task_definition=fargate_task_definition,
            desired_count=mincount,
            enable_ecs_managed_tags=True,
        )
        permissions.append(
            iam.PolicyStatement(actions=["sqs:*"], resources=[queue.queue_arn],)
        )

        scaling = fargate_service.auto_scale_task_count(
            min_capacity=mincount, max_capacity=maxcount,
        )
        scaling.scale_on_cpu_utilization("CpuScaling", target_utilization_percent=50)

        scaling.scale_on_metric(
            "QueueMessagesVisibleScaling",
            metric=queue.metric_approximate_number_of_messages_visible(),
            scaling_steps=[
                ScalingInterval(change=-5, upper=0),
                ScalingInterval(change=+5, lower=1),
            ],
        )

        for perm in permissions:
            fargate_service.task_definition.task_role.add_to_policy(perm)
