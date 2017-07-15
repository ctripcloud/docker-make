# reference for .docker-make.yml

## tag-names(essential, list of dict, default: [])
definition of customized tag names.

### `name` (essential, string)
name of the new customized tag, which can be referred in a tag template.

### `type` (essential, string)
type of the new customized tag which produces a tag name based on the value of `value` field, choices include:
* `datetime`
* `cmd`

### `value` (essential, string)
argument passed to the tag name generator specified by the `type` field:
* for `datetime` type, value is a Python datetime formatter, e.g '%Y%m%d%H%M'.
* for `cmd` type, value is a shell command, e.g. `echo hello-world`.


## builds(essential, dict, default: {})
definition of `docker-builds` and their relationships.

### name of build(e.g, `dwait` and `dresponse`) (essential, string)
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
