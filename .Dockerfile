FROM ubuntu:22.04


WORKDIR /root/projects
ARG DEBIAN_FRONTEND=noninteractive
# Timezone
ENV TZ="Asia/Bangkok"

# https://github.com/pyenv/pyenv/wiki#suggested-build-environment
RUN apt update && apt upgrade -y
RUN apt install -y build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
# Set timezone
RUN apt install -y tzdata
RUN ln -snf /usr/share/zoneinfo/$CONTAINER_TIMEZONE /etc/localtime && echo $CONTAINER_TIMEZONE > /etc/timezone
# Set locales
# https://leimao.github.io/blog/Docker-Locale/
RUN apt-get install -y locales
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LC_ALL en_US.UTF-8 
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  

# Add display adapter
ENV DISPLAY host.docker.internal:0.0

# For Download imerg
RUN apt install wget -y

# Python
RUN apt install -y python3 python3-pip
RUN pip install ipykernel
RUN pip install ipywidgets
RUN pip install numpy
RUN pip install pandas
RUN pip install matplotlib
RUN pip install scikit-learn
# Read IMERG
RUN pip install h5py
RUN pip install wget
# Read GSMaP
RUN pip install basemap
RUN pip install netCDF4
# Interpolate
RUN pip install --timeout=1000 pyinterpolate

# rasterio
RUN apt install gdal-bin libgdal-dev -y
RUN export CPLUS_INCLUDE_PATH=/usr/include/gdal
RUN export C_INCLUDE_PATH=/usr/include/gdal
RUN pip install GDAL==3.4.1
RUN pip install --timeout=1000 rasterio
RUN pip install rioxarray

# ML
RUN pip install xgboost
RUN pip install lightgbm

RUN apt install -y ssh

ADD ssh-config /root/.ssh/config
RUN chmod 700 /root/.ssh/config

CMD tail -f /bin/bash