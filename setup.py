#!/usr/bin/env python
from distutils.version import LooseVersion
from setuptools import setup, find_packages


def get_docker_client_requirement():
    DOCKER_PY_REQUIREMENT = 'docker-py >= 1.8.1, < 2'
    DOCKER_RRQUIREMENT = 'docker >= 2.0.0, < 3'
    docker_client_installed = True
    try:
        import docker
    except ImportError:
        docker_client_installed = False
    if docker_client_installed and\
       LooseVersion(docker.__version__) < LooseVersion('2.0.0'):
        return DOCKER_PY_REQUIREMENT
    return DOCKER_RRQUIREMENT


def find_requirements(fn):
    lines = []
    with open(fn) as f:
        for line in f:
            line = line.strip()
            if not line.startswith('#'):
                lines.append(line)
    return lines


setup(
    name='docker-make',
    description='build,tag,and push a bunch of related docker images via a single command',
    version='1.1.7',
    author='jizhilong',
    author_email='zhilongji@gmail.com',
    url='https://github.com/CtripCloud/docker-make',
    license='Apache',
    keywords=['docker', 'image',' build'],
    packages=find_packages(exclude=['tests']),
    entry_points={
        'console_scripts': [
            'docker-make = dmake.cli:main'
        ]
    },
    install_requires=find_requirements('requirements.pip') +\
                     [get_docker_client_requirement()],
    tests_require=find_requirements('test-requirements.pip'),
    test_suite='nose.collector',
    classifiers=[],
    )
