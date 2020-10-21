"""cdk_watchbot.lambdaStack: SQS + SNS + LAMBDA."""

from typing import Dict, Optional, List

import os

import docker
from aws_cdk import (
    core,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as sns_sub,
    aws_iam as iam,
    aws_lambda,
    aws_lambda_event_sources,
)


class Lambda(core.Stack):
    """Lambda Watchbot Stack."""

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        handler: str,
        runtime: aws_lambda.Runtime = aws_lambda.Runtime.PYTHON_3_7,
        memory: int = 3008,
        timeout: int = 900,
        concurrent: int = 10,
        retry: int = 0,
        permissions: Optional[List[iam.PolicyStatement]] = None,
        env: Dict = {},
        code_dir: str = "./",
        **kwargs,
    ) -> None:
        """Create AWS Lambda watchbot stack. """
        super().__init__(scope, id, **kwargs)

        permissions = permissions or []

        topic = sns.Topic(self, "Topic", display_name="Lambda Watchbot SNS Topic")
        dlqueue = sqs.Queue(self, "DeadLetterQueue")
        queue = sqs.Queue(
            self,
            "Queue",
            visibility_timeout=core.Duration.seconds(timeout),
            dead_letter_queue=sqs.DeadLetterQueue(queue=dlqueue, max_receive_count=3),
        )

        topic.add_subscription(sns_sub.SqsSubscription(queue))

        worker = aws_lambda.Function(
            self,
            f"{id}-lambda",
            description="Watchbot's worker",
            runtime=runtime,
            code=self.create_package(code_dir),
            handler=handler,
            memory_size=memory,
            reserved_concurrent_executions=concurrent,
            timeout=core.Duration.seconds(timeout),
            retry_attempts=retry,
            environment=env,
        )

        for perm in permissions:
            worker.add_to_role_policy(perm)

        worker.add_event_source(
            aws_lambda_event_sources.SqsEventSource(queue, batch_size=1)
        )
        topic.grant_publish(worker)

    def create_package(self, code_dir: str) -> aws_lambda.Code:
        """Build docker image and create package."""
        print("Creating lambda package [running in Docker]...")
        client = docker.from_env()

        print("Building docker image...")
        client.images.build(
            path=code_dir,
            dockerfile="Dockerfile",
            tag="lambda:latest",
            rm=True,
        )

        print("Copying package.zip ...")
        client.containers.run(
            image="lambda:latest",
            command="/bin/sh -c 'cp /tmp/package.zip /local/package.zip'",
            remove=True,
            volumes={os.path.abspath(code_dir): {"bind": "/local/", "mode": "rw"}},
            user=0,
        )

        return aws_lambda.Code.asset(os.path.join(code_dir, "package.zip"))
