"""Setup."""

from setuptools import find_packages, setup

# Runtime requirements.
inst_reqs = [
    "rio-tiler>=2.0,<2.1",
    "rio-tiler-pds>=0.4,<1.0",
    "cogeo-mosaic>=3.0.0rc2,<3.1",
]

extra_reqs = {
    "test": ["pytest", "pytest-cov"],
    "deploy": [
        "aws-cdk.core==1.76.0",
        "aws-cdk.aws_lambda==1.76.0",
        "aws-cdk.aws_lambda_event_sources==1.76.0",
        "aws-cdk.aws_sqs==1.76.0",
        "aws-cdk.aws_sns==1.76.0",
        "aws-cdk.aws_ecs==1.76.0",
        "aws-cdk.aws_ec2==1.76.0",
        "aws-cdk.aws_ecr_assets==1.76.0",
        "aws-cdk.aws_autoscaling==1.76.0",
        "aws-cdk.aws_ecs_patterns==1.76.0",
    ],
}

setup(
    name="tilebot",
    version="0.1.0",
    python_requires=">=3.7",
    packages=find_packages(exclude=["tests"]),
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)
