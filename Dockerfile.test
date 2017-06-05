FROM python:2.7.11
MAINTAINER Ji.Zhilong <zhilongji@gmail.com>

ADD . /usr/local/src/docker-make
WORKDIR /usr/local/src/docker-make

RUN pip install . &&\
    pip install -r test-requirements.pip &&\
    flake8 dmake && nosetests tests/
