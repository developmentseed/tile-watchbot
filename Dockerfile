FROM lambgeo/lambda-gdal:3.2-python3.8 as gdal

COPY setup.py setup.py
COPY app/ app/

RUN pip install . -t /opt/python  --no-binary numpy,rasterio --no-cache

FROM public.ecr.aws/lambda/python:3.8

# Bring C libs from lambgeo/lambda-gdal image
COPY --from=gdal /opt/lib/ /opt/lib/
COPY --from=gdal /opt/include/ /opt/include/
COPY --from=gdal /opt/share/ /opt/share/
COPY --from=gdal /opt/bin/ /opt/bin/

COPY --from=gdal /opt/python ${LAMBDA_TASK_ROOT}

ENV \
    GDAL_DATA=/opt/share/gdal \
    PROJ_LIB=/opt/share/proj \
    GDAL_CONFIG=/opt/bin/gdal-config \
    GEOS_CONFIG=/opt/bin/geos-config \
    PATH=/opt/bin:$PATH
