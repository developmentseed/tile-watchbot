"""cdk_watchbot.lambdaStack: SQS + SNS + LAMBDA/ECS."""

from typing import Any, Dict, List, Optional, Union

# from aws_cdk.aws_applicationautoscaling import ScalingInterval
from aws_cdk import aws_applicationautoscaling as auto_scale
from aws_cdk import aws_cloudwatch
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_events, aws_events_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda, aws_lambda_event_sources, aws_logs
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as sns_sub
from aws_cdk import aws_sqs as sqs
from aws_cdk import core


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

        fargate_task_definition = ecs.FargateTaskDefinition(
            self, "FargateTaskDefinition", memory_limit_mib=memory, cpu=cpu,
        )
        log_driver = ecs.AwsLogDriver(
            stream_prefix=f"/ecs/tilebot/{id}",
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
        )

        fargate_task_definition.add_container(
            "FargateContainer",
            image=ecs.ContainerImage.from_asset(directory="./"),
            entry_point=entrypoint,
            environment=environment,
            logging=log_driver,
        )

        fargate_service = ecs.FargateService(
            self,
            "FargateService",
            cluster=cluster,
            task_definition=fargate_task_definition,
            desired_count=mincount,
            enable_ecs_managed_tags=True,
            assign_public_ip=True,
        )
        permissions.append(
            iam.PolicyStatement(actions=["sqs:*"], resources=[queue.queue_arn],)
        )
        for perm in permissions:
            fargate_service.task_definition.task_role.add_to_policy(perm)

        total_number_of_message_lambda = aws_lambda.Function(
            self,
            f"{id}-TotalMessagesLambda",
            description="Create TotalNumberOfMessage metrics",
            code=aws_lambda.Code.from_inline(
                """const AWS = require('aws-sdk');
    exports.handler = function(event, context, callback) {
    const sqs = new AWS.SQS({ region: process.env.AWS_DEFAULT_REGION });
    const cw = new AWS.CloudWatch({ region: process.env.AWS_DEFAULT_REGION });
    return sqs.getQueueAttributes({
        QueueUrl: process.env.SQS_QUEUE_URL,
        AttributeNames: ['ApproximateNumberOfMessagesNotVisible', 'ApproximateNumberOfMessages']
    }).promise()
    .then((attrs) => {
        return cw.putMetricData({
            Namespace: 'AWS/SQS',
            MetricData: [{
            MetricName: 'TotalNumberOfMessages',
            Dimensions: [{ Name: 'QueueName', Value: process.env.SQS_QUEUE_NAME }],
            Value: Number(attrs.Attributes.ApproximateNumberOfMessagesNotVisible) +
                    Number(attrs.Attributes.ApproximateNumberOfMessages)
            }]
        }).promise();
    })
    .then((metric) => callback(null, metric))
    .catch((err) => callback(err));
};"""
            ),
            handler="index.handler",
            runtime=aws_lambda.Runtime.NODEJS_10_X,
            timeout=core.Duration.seconds(60),
            environment={
                "SQS_QUEUE_URL": queue.queue_url,
                "SQS_QUEUE_NAME": queue.queue_name,
            },
        )
        total_number_of_message_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sqs:GetQueueAttributes"], resources=[queue.queue_arn],
            )
        )
        total_number_of_message_lambda.add_to_role_policy(
            iam.PolicyStatement(actions=["cloudwatch:PutMetricData"], resources=["*"],)
        )
        total_number_of_message_lambda.add_to_role_policy(
            iam.PolicyStatement(actions=["logs:*"], resources=["arn:aws:logs:*:*:*"],)
        )

        rule = aws_events.Rule(
            self,
            "TotalMessagesSchedule",
            schedule=aws_events.Schedule.rate(core.Duration.seconds(60)),
        )
        rule.add_target(
            aws_events_targets.LambdaFunction(total_number_of_message_lambda)
        )

        scalable_target = auto_scale.ScalableTarget(
            self,
            "AutoScallingTarget",
            min_capacity=mincount,
            max_capacity=maxcount,
            service_namespace=auto_scale.ServiceNamespace.ECS,
            resource_id="/".join(
                ["service", cluster.cluster_name, fargate_service.service_name]
            ),
            scalable_dimension="ecs:service:DesiredCount",
        )
        scalable_target.node.add_dependency(fargate_service)

        scale_up = auto_scale.CfnScalingPolicy(
            self,
            "ScaleUp",
            policy_name="PolicyScaleUp",
            policy_type="StepScaling",
            scaling_target_id=scalable_target.scalable_target_id,
            step_scaling_policy_configuration=auto_scale.CfnScalingPolicy.StepScalingPolicyConfigurationProperty(
                adjustment_type="ChangeInCapacity",
                cooldown=300,
                metric_aggregation_type="Maximum",
                step_adjustments=[
                    auto_scale.CfnScalingPolicy.StepAdjustmentProperty(
                        scaling_adjustment=5, metric_interval_lower_bound=0,
                    ),
                ],
            ),
        )
        scale_up_trigger = aws_cloudwatch.CfnAlarm(  # noqa
            self,
            "ScaleUpTrigger",
            alarm_description="Scale up due to visible messages in queue",
            dimensions=[
                aws_cloudwatch.CfnAlarm.DimensionProperty(
                    name="QueueName", value=queue.queue_name,
                ),
            ],
            metric_name="ApproximateNumberOfMessagesVisible",
            namespace="AWS/SQS",
            evaluation_periods=1,
            comparison_operator="GreaterThanThreshold",
            period=300,
            statistic="Maximum",
            threshold=0,
            alarm_actions=[scale_up.ref],
        )

        scale_down = auto_scale.CfnScalingPolicy(
            self,
            "ScaleDown",
            policy_name="PolicyScaleDown",
            policy_type="StepScaling",
            scaling_target_id=scalable_target.scalable_target_id,
            step_scaling_policy_configuration=auto_scale.CfnScalingPolicy.StepScalingPolicyConfigurationProperty(
                adjustment_type="ExactCapacity",
                cooldown=300,
                step_adjustments=[
                    auto_scale.CfnScalingPolicy.StepAdjustmentProperty(
                        scaling_adjustment=mincount, metric_interval_upper_bound=0,
                    ),
                ],
            ),
        )

        scale_down_trigger = aws_cloudwatch.CfnAlarm(  # noqa
            self,
            "ScaleDownTrigger",
            alarm_description="Scale down due to lack of in-flight messages in queue",
            dimensions=[
                aws_cloudwatch.CfnAlarm.DimensionProperty(
                    name="QueueName", value=queue.queue_name,
                ),
            ],
            metric_name="TotalNumberOfMessages",
            namespace="AWS/SQS",
            evaluation_periods=1,
            comparison_operator="LessThanThreshold",
            period=600,
            statistic="Maximum",
            threshold=1,
            alarm_actions=[scale_down.ref],
        )
