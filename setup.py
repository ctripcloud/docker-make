#!/usr/bin/env python

from distutils.core import setup


def find_requirements():
    ret = []
    with open('requirements.pip') as f:
        for line in f:
            if not line.startswith('#'):
                ret.append(line)
    return ret


setup(
    name='docker-make',
    description='a tool for simplifying docker image building and pushing',
    version='1.0',
    author='jizhilong',
    author_email='zhilongji@gmail.com',
    url='https://github.com/CtripCloud/docker-make',
    license='Apache',
    keywords=['docker', 'image',' build'],
    scripts=['docker-make'],
    install_requires=find_requirements(),
    classifiers=[],
    )
