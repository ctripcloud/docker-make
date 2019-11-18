FROM python:2.7.11
ARG ENV_VAR
#MAINTAINER Ji.Zhilong <zhilongji@gmail.com>

ENV ENV_VAR=${ENV_VAR}

#ADD requirements.pip /tmp/
#RUN pip install -r /tmp/requirements.pip
#
#ADD . /usr/local/src/docker-make
#
#RUN pip install /usr/local/src/docker-make
