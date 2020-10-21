# tile-watchbot

Create Tiles ... a lot of tiles


### 1. Deploy STACK

add `.env` in `/stack` with the wanted config (or use environment variables)

```
STACK_OWNER=vincents
STACK_CLIENT=cccmc
STACK_PROJECT=rubber-risk

STACK_MOSAIC_BACKEND=dynamodb://
STACK_MOSAIC_HOST=us-west-2/ds-mosaics

STACK_STAGE=production
STACK_BUCKETS='["ds-satellite-us-west-2", "sentinel-cogs"]'

STACK_OUTPUT_BUCKET=ds-satellite-us-west-2
````

`AWS_DEFAULT_REGION=us-west-2 AWS_REGION=us-west-2 cdk deploy`

### 2. Send jobs

- Create list of tiles in form of `Z-X-Y`
```
$ cat my.geojson| supermercado burn 14 | xt -d'-' > list_z14.txt
```

- use python script to send jobs to SQS/Lambda
```
$ cd scripts/
$ cat ../list_tiles.txt | python -m create_jobs \
    --layer cccmc.sentinel2_winter2018 \
    --topic arn:aws:sns:us-west-2:552819999234:tilebot-lambda-production-TopicBFC7AF6E-1CNDRSH5TB850
```
