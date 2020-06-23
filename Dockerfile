# Pull base image.
FROM python:3.8.3-buster
#FROM ubuntu:16.04
#FROM alpine:3.7

RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Define workdir
WORKDIR /root/distcrs

# Install some tools: gcc build tools, unzip, etc
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install curl build-essential unzip cmake git #python3 python3-setuptools python3-pip

#RUN pip3 install py_ecc
RUN pip install py_ecc


# Define default command
CMD ["bash"]