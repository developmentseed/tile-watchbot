FROM lambgeo/lambda-gdal:3.2-python3.8 as gdal

COPY setup.py setup.py
COPY app/ app/

RUN pip install . -t /opt/python  --no-binary numpy,rasterio,pygeos,pydantic --no-cache

RUN find /opt/python -type d -a -name 'tests' -print0 | xargs -0 rm -rf
RUN find /opt/python -type f -name '*.pyc' | while read f; do n=$(echo $f | sed 's/__pycache__\///' | sed 's/.cpython-[2-3][0-9]//'); cp $f $n; done;
RUN find /opt/python -type d -a -name '__pycache__' -print0 | xargs -0 rm -rf
RUN find /opt/python -type f -a -name '*.py' -print0 | xargs -0 rm -f
RUN cd /opt && find lib -name \*.so\* -exec strip {} \;

RUN rm -rf /opt/share/aclocal \
    && rm -rf /opt/share/doc \
    && rm -rf /opt/share/man \
    && rm -rf /opt/share/hdf*

FROM public.ecr.aws/lambda/python:3.8

# Bring C/python libs from lambgeo/lambda-gdal image
COPY --from=gdal /opt/lib/ /opt/lib/
COPY --from=gdal /opt/share/ /opt/share/
COPY --from=gdal /opt/bin/ /opt/bin/
COPY --from=gdal /opt/python ${LAMBDA_TASK_ROOT}

ENV \
    GDAL_DATA=/opt/share/gdal \
    PROJ_LIB=/opt/share/proj \
    GDAL_CONFIG=/opt/bin/gdal-config \
    GEOS_CONFIG=/opt/bin/geos-config \
    PATH=/opt/bin:/opt/python/bin:$PATH
