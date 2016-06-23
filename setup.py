#!/usr/bin/env python

from distutils.core import setup

setup(
    name='docker-make',
    description='a tool for simplifying docker image building and pushing',
    version='1.1.2',
    author='jizhilong',
    author_email='zhilongji@gmail.com',
    url='https://github.com/CtripCloud/docker-make',
    license='Apache',
    keywords=['docker', 'image',' build'],
    scripts=['docker-make'],
    install_requires=[
        'PyYAML >= 3.10, < 4',
        'docker-py >= 1.8.1, < 2',
    ],
    classifiers=[],
    )
