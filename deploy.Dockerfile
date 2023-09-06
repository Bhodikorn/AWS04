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

# For Download imerg
RUN apt install -y wget

RUN apt install -y python3 python3-pip

# GDAL
RUN apt install -y gdal-bin libgdal-dev
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
RUN pip3 install GDAL==3.4.1

# Other packages
RUN pip3 install basemap==1.3.6
RUN pip3 install h5py==3.8.0
RUN pip3 install ipykernel==6.22.0
RUN pip3 install ipywidgets==8.0.5
RUN pip3 install lightgbm==3.3.5
RUN pip3 install matplotlib==3.6.3
RUN pip3 install netCDF4==1.6.3
RUN pip3 install numpy==1.23.5
RUN pip3 install pandas==1.5.3
RUN pip3 install pyinterpolate==0.3.7
RUN pip3 install rasterio==1.3.6
RUN pip3 install rioxarray==0.14.0
RUN pip3 install scikit-learn==1.2.2
RUN pip3 install wget==3.2
RUN pip3 install xgboost==1.7.4

RUN apt install -y dos2unix

CMD /bin/bash -c "dos2unix main.sh ; sh main.sh"