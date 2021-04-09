FROM public.ecr.aws/lambda/python:3.8

COPY tilebot/ tilebot/
COPY setup.py setup.py

RUN pip install -e . rasterio==1.1.8
