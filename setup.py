"""Setup."""

from setuptools import setup, find_packages

# Runtime requirements.
inst_reqs = [
    "rio-tiler~=2.0.0b17",
    "rio-tiler-pds~=0.3.2",
    "cogeo-mosaic @ git+https://github.com/developmentseed/cogeo-mosaic.git@281d417229d77ba5cd4f0ad702b85cb3b51be43c",
]

extra_reqs = {
    "deploy": [
        "docker",
        "aws-cdk.core",
        "aws-cdk.aws_lambda",
        "aws-cdk.aws_sqs",
        "aws-cdk.aws_sns",
        "aws-cdk.aws_ec2",
    ],
}

setup(
    name="app",
    version="0.1.0",
    python_requires=">=3.7",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)
