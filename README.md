# docker-make: simplify builds of related docker images.
`docker-make` is a command line tool inspired by [docker-compose](https://www.docker.com/products/docker-compose), while `docker-compose`
focus on managing the lifecycle of a bunch of related docker containers, `docker-make` aimes at simplify and automate the procedure of
building,tagging,and pusing a bunch of related docker images.

## table of contents
- [Install](#installation)
  * [via pip](#install-via-pip)
  * [via alias to docker run](#instanll-via-alias-to-docker-run)
- [Quickstart](#quickstart)
- [Use Cases](#typical-use-cases)
  * [single image-tag,push on condition](#single-image-tagpush-on-condition)
  * [two images-one for compile, one for deployment](#two-images-one-for-compile-one-for-deployment)
  * [two images-one for deploy, one for unit tests](#two-images-one-for-deploy-one-for-unit-tests)
  * [several images-one as base with tools, others for different applications](#several-images-one-as-base-with-tools-others-for-different-applications)
- [CLI reference](#command-line-reference)
- [.docker-make.yml reference](#docker-makeyml)

## installation
### install via pip
`docker-make` is a Python project, so you can install it via pip:

```bash
pip install docker-make
```

### install via alias to docker run
or you can just execute it with a `docker run` command, and for convenience, you can set an alias:

```bash
alias docker-make="docker run --rm -w /usr/src/app\\
                                   -v ~/.docker:/root/.docker\\
                                   -v /var/run/docker.sock:/var/run/docker.sock\\
                                   -v \"\$(pwd)\":/usr/src/app jizhilong/docker-make docker-make"
```


## quickstart
`docker-make` is a user is itself, so you can build a image for it with the following command:

```bash
git clone https://github.com/CtripCloud/docker-make.git
cd docker-make
docker-make --no-push
``` 

if all goes well, the console output would look like:

```
INFO 2016-06-19 01:21:49,513 docker-make(277) docker-make: building
INFO 2016-06-19 01:21:49,657 docker-make(277) docker-make: attaching labels
INFO 2016-06-19 01:21:49,748 docker-make(277) docker-make: label added: com.dockermake.git.commitid="3d97f0fc382e1f90f77584bbc8193509b835fce0"
INFO 2016-06-19 01:21:49,748 docker-make(277) docker-make: build succeed: c4391b6110f6
INFO 2016-06-19 01:21:49,756 docker-make(277) docker-make: tag added: jizhilong/docker-make:3d97f0fc382e1f90f77584bbc8193509b835fce0
INFO 2016-06-19 01:21:49,760 docker-make(277) docker-make: tag added: jizhilong/docker-make:latest
```

## how it works
docker-make read and parse `.docker-make.yml`(configurable via command line) in the root of a git repo,
in which you spcify images to build, each build's Dockerfile, context, repo to push, rules for tagging, dependencies, etc.

With information parsed from `.docker-make.yml`, `docker-make` will build, tag, push images in a appropriate order with
regarding to dependency relations.

## typical use cases
### single image-tag,push on condition
this is the most common use case, and `docker-compose` belongs to such case:

```yaml
builds:
  docker-make:
    context: /
    dockerfile: Dockerfile
    pushes:
      - 'always=jizhilong/docker-make:{fcommitid}'
      - 'on_tag=jizhilong/docker-make:{git_tag}'
      - 'on_branch:master=jizhilong/docker-make:latest'
    labels:
      - 'com.dockermake.git.commitid={fcommitid}'
    dockerignore:
      - .git
```

### two images-one for compile, one for deployment

```yaml
builds:
  dwait:
    context: /
    dockerfile: Dockerfile.dwait
    extract:
      - /usr/src/dwait/bin/.:./dwait.bin.tar

  dresponse:
    context: /
    dockerfile: Dockerfile
    pushes:
      - 'on_branch:master=hub.privateregistry.com/dresponse:latest'
      - 'on_branch:master=hub.privateregistry.com/dresponse:{fcommitid}'
    depends_on:
      - dwait
```

In this case, golang codes of the project are compiled in `dwait`, the compiled binary is extracted out by `docker-make`
and installed to `dresponse` with a `ADD` instruction in `dresponse`'s Dockerfile.Finally, `dresponse` is pushed to a private
registry with two tags, git sha-1 commit id and 'latest'.
With `docker-make`, you can do all of these steps properly via a single command；

```
$ docker-make
INFO 2016-06-19 21:06:09,088 docker-make(278) dwait: building
INFO 2016-06-19 21:06:09,440 docker-make(278) dwait: build succeed: ed169e889ecc
INFO 2016-06-19 21:06:09,440 docker-make(278) dwait: extracting archives
INFO 2016-06-19 21:06:09,599 docker-make(278) dwait: extracting archives succeed
INFO 2016-06-19 21:06:09,600 docker-make(278) dresponse: building
INFO 2016-06-19 21:06:10,305 docker-make(278) dresponse: build succeed: 671062910765
INFO 2016-06-19 21:06:10,318 docker-make(278) dresponse: tag added: hub.privateregistry.com/dresponseagent:latest
INFO 2016-06-19 21:06:10,325 docker-make(278) dresponse: tag added: hub.privateregistry.com/dresponseagent:a06fbc3a8af2f0fd12e89f539e481fe7d425c7c3
INFO 2016-06-19 21:06:10,325 docker-make(278) dresponse: pushing to hub.privateregistry.com/dresponseagent:latest
INFO 2016-06-19 21:06:17,576 docker-make(278) dresponse: pushed to hub.privateregistry.com/dresponseagent:latest
INFO 2016-06-19 21:06:17,576 docker-make(278) dresponse: pushing to hub.privateregistry.com/dresponseagent:a06fbc3a8af2f0fd12e89f539e481fe7d425c7c3
INFO 2016-06-19 21:06:18,505 docker-make(278) dresponse: pushed to hub.privateregistry.com/dresponseagent:a06fbc3a8af2f0fd12e89f539e481fe7d425c7c3
```

while the equivalent raw `docker` commands could be quite long, and require a careful atttension to the order of commands:

```bash
$ docker build -t dmake -f Dockerfile.dwait
$ tmp_container=`docker create dmake`
$ docker cp $tmp_container:/usr/src/dwait/bin dwait.bin.tar
$ docker build -t dresponse Dockerfile
$ docker tag dresponsehu b.privateregistry.com/dresponse:latest
$ docker tag dresponsehu b.privateregistry.com/dresponse:${git rev-parse HEAD}
```

### two images-one for deploy, one for unit tests

```yaml
builds:
  novadocker:
    context: /
    dockerfile: dockerfiles/Dockerfile
    pushes:
      - 'on_tag=hub.privateregistry.com/novadocker:{git_tag}'
    dockerignore:
      - .dmake.yml
      - .gitignore
      - tools
      - contrib
      - doc
    labels:
      - "com.dockermake.git.commitid={fcommitid}"

  novadocker-test:
    context: dockerfiles/
    dockerfile: Dockerfile.test
    rewrite_from: novadocker
    depends_on:
      - novadocker
```

In this case, `novadocker` is built for deployment, `novadocker-teset` inherits from it via a 'FROM' instruction.
The primary content of 'Dockerfile.test' includes installing testing dependencies and running the unit tests, if
the tests pass, `docker build` will succeed, otherwise it will fail.Finally, `novadocker` will be pushed to a private
registry, if the image is built on a git tag.

The equivalent job could be expressed with some bash scripts.

```bash
set -e
fcommitid=`git rev-parse HEAD`
docker build -t novadocker -f dockerfiles/Dockerfile --label com.dockermake.git.commitid=$fcommitid .
docker build -t novadocker-test -f dockerfiles/Dockerfile.test .

if git show-ref --tags|grep $fcommitid; then
   tagname=`git describe` 
   docker tag novadocker hub.privateregistry.com/novadocker:$tagname
   docker push novadocker hub.privateregistry.com/novadocker:$tagname
fi
```

### several images-one as base with tools, others for different applications

```yaml
builds:
  base:
    context: base
    dockerfile: Dockerfile

  java:
    context: java
    dockerfile: Dockerfile
    rewrite_from: base
    depends_on:
      - base

  php:
    context: php
    dockerfile: Dockerfile
    rewrite_from: base
    depends_on:
      - base

  java-app1:
    context: app1
    dockerfile: Dockerfile
    rewrite_from: java
    depends_on:
      - java

  php-app1:
    context: app2
    dockerfile: Dockerfile
    rewrite_from: php 
    depends_on:
      - php
```

In such case, libraries like libc and monitoring tools are installed in base's Dockerfile.
A java runtime environment and a php runtime environment are built by inheriting from the base image.
With java and php as the base images, a java app and a php app are built.

## command line reference

```bash
$ docker-make --help
usage: docker-make [-h] [-f DMAKEFILE] [-d] [--dry-run] [--no-push]
                   [builds [builds ...]]

build docker images in a simpler way.

positional arguments:
  builds                builds to execute.

optional arguments:
  -h, --help            show this help message and exit
  -f DMAKEFILE, --file DMAKEFILE
                        path to docker-make configuration file.
  -d, --detailed        print out detailed logs
  --dry-run             print docker commands only
  --no-push             build only, dont push
```

## .docker-make.yml

### builds(rservered keyword)
`builds` is a reserved a keyword for docker-make, you should define your builds under this section.

### `dwait` and `dresponse` (essential, string)
names for your build.

### `context` (essential, string)
path to build context, relative to the root of the repo.

### `dockerfile` (essential, string)
Dockerfile for the build, relative to the context.

### `pushes` (optional, [string], default: [])
pushing rule for the built image, a single rule is composed in a form of  '<push_mode>=<repo>:<tag_template>',
in which:
* `push_mode` defines when to push, choices include:
  * `always`: always push the successfully built image.
  * `on_tag`: push if built on a git tag.
  * `on_branch:<branchname>`: push if built on branch `branchname`

* `repo` defines which repo to push to.

* `tag_template` is a python formattable string for generating the image tag, available template variables include:
  * `date`: date of the built(e.g, 20160617)
  * `scommitid`: a 7-char trunc of the corresponding git sha-1 commit id.
  * `fcommitid`: full git commit id.
  * `git_tag`: git tag name (if built on a git tag)
  * `git_branch`: git branch name(if built on a git branch)

### `dockerignore` (optional, [string], default: [])
files or directories you want ignore in the context, during `docker build`
ref: [dockerignore](https://docs.docker.com/engine/reference/builder/#dockerignore-file)

### `labels` (optional, [string])
define labels applied to built image, each item should be with format '<key>="<value>"', with `<value>`
being a python template string, available template variables include:
* `scommitid`: a 7-char trunc of the corresponding git sha-1 commit id.
* `fcommitid`: full git commit id.
* `git_tag`: git tag name (if built on a git tag)
* `git_branch`: git branch name(if built on a git branch)

### `depends_on` (optional, [string], default: [])
which builds this build depends on, `docker-make` will build the depends first.

### `extract` (optional, [string], default: [])
define a list of source-destination pairs, with `source` point to a path of the newly built image, and `destination` being a filename on the host, `docker-make` will package `source` in a tar file, and copy the tar file to `destination`. Each item's syntax is similar to `docker run -v`

### `rewrite_from` (optional, string, default: '')
a build's name which should be available in `.docker-make.yml`, if supplied, `docker-make` will build `rewrite_from` first, and replace current build's Dockerfile's `FROM` with `rewrite_from`'s fresh image id.
