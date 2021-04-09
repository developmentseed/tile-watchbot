# tile-watchbot

Create Tiles ... a lot of tiles

## 1. Deploy STACK

add `.env` in `/stack` with the wanted config (or use environment variables)

```
STACK_OWNER=user
STACK_CLIENT=someone
STACK_PROJECT=myproject

STACK_MOSAIC_BACKEND=dynamodb://
STACK_MOSAIC_HOST=us-west-2/mosaics

STACK_STAGE=production
STACK_BUCKETS='["mybucket-us-west-2", "*sentinel-cogs*"]'

STACK_OUTPUT_BUCKET=mybucket-us-west-2
```
#### Install CDK
`npm install -g aws-cdk@1.76.0`

#### Lambda
`cdk deploy tilebot-lambda-production`

#### ECS - Fargate
`cdk deploy tilebot-ecs-production`

## 2. Send jobs

- Create list of tiles in form of `Z-X-Y`
```
$ cat my.geojson| supermercado burn 14 | xt -d'-' > list_z14.txt
```

- use python script to send jobs to SQS/Lambda
```
$ cd scripts/
$ cat ../list_tiles.txt | python -m create_jobs - \
    --dataset mosaicid://username.layer \
    --reader rio_tiler_pds.sentinel.aws.S2COGReader \
    --expression "B02,B8A,B11,B12,(B08 - B04) / (B08 + B04),1.5 * (B08-B04) / (0.5 + B08 + B04)" \
    --topic arn:aws:sns:us-west-2:1111111111:tilebot-lambda-production-TopicAAAAAAAAAAAAAAAAAA
```
