"""Setup."""

from setuptools import setup, find_packages

# Runtime requirements.
inst_reqs = [
    "rio-tiler==2.0.0rc3",
    "rio-tiler-pds==0.4.1",
    "cogeo-mosaic==3.0.0a18",
]

extra_reqs = {
    "test": ["pytest", "pytest-cov"],
    "deploy": [
        "aws-cdk.core==1.76.0",
        "aws-cdk.aws_lambda==1.76.0",
        "aws-cdk.aws_sqs==1.76.0",
        "aws-cdk.aws_sns==1.76.0",
        "aws-cdk.aws_ec2==1.76.0",
        "aws-cdk.aws_ecr_assets==1.76.0",
    ],
}

setup(
    name="app",
    version="0.1.0",
    python_requires=">=3.7",
    packages=find_packages(exclude=["tests"]),
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)
