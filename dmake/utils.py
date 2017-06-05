import os
import logging

import yaml
import docker
from distutils.version import LooseVersion
from docker import utils as docker_utils

from dmake.errors import *  # noqa


LOG = logging.getLogger(__name__)
_docker = None


class _GarbageCleaner(object):
    def __init__(self):
        self._files = set()

    def register(self, filename):
        self._files.add(filename)

    def clean(self, filename):
        LOG.debug("cleaning up %s" % filename)
        if not os.path.exists(filename):
            return
        if os.path.isfile(filename) or os.path.islink(filename):
            os.remove(filename)
        if os.path.isdir(filename):
            os.rmdir(filename)

    def clean_all(self):
        for filename in self._files:
            self.clean(filename)


GarbageCleaner = _GarbageCleaner()


def docker_client():
    global _docker
    if _docker is None:
        params = docker_utils.kwargs_from_env()
        params['version'] = 'auto'
        if LooseVersion(docker.__version__) < LooseVersion('2.0.0'):
            _docker = docker.client.Client(**params)
        else:
            _docker = docker.api.client.APIClient(**params)
    return _docker


def load_yaml(filename='.docker-make.yml'):
    try:
        with open(filename) as f:
            return yaml.safe_load(f)
    except (IOError, yaml.YAMLError) as e:
        err_msg = getattr(e, '__module__', '') + '.' + e.__class__.__name__
        raise ConfigurationError(u"{}: {}".format(err_msg, e))


def validate(config):
    builds = config.get('builds')
    if builds is None:
        raise ValidateError("no builds specified")
    if not isinstance(builds, dict):
        raise ValidateError("builds should be a dict")

    for name, build in builds.iteritems():
        for dep in build.get('depends_on', []):
            if dep not in builds:
                raise ValidateError("%s depends on %s, which is not present in"
                                    "the current configuration." % (name, dep))
    return True


def sort_builds_dict(builds):
    # Topological sort (Cormen/Tarjan algorithm)
    unmarked = builds.keys()
    temporary_marked = set()
    sorted_builds = []

    def visit(n):
        if n in temporary_marked:
            if n in builds[n].get('depends_on', []):
                raise DependencyError('A build can not'
                                      ' depend on itself: %s' % n['name'])
            raise DependencyError('Circular dependency between %s' %
                                  ' and '.join(temporary_marked))

        if n in unmarked:
            temporary_marked.add(n)
            builds_dep_on_n = [name for name, build in builds.iteritems()
                               if
                               n in build.get('depends_on', [])]
            for m in builds_dep_on_n:
                visit(m)
            temporary_marked.remove(n)
            unmarked.remove(n)
            sorted_builds.insert(0, n)

    while unmarked:
        visit(unmarked[-1])

    return sorted_builds


def get_sorted_build_dicts_from_yaml(filename):
    config = load_yaml(filename)
    validate(config)
    builds = config["builds"]
    builds_order = sort_builds_dict(builds)
    return builds_order, builds


def expand_wants(candidates, wants):
    ret = set()
    wants = set(wants)
    while wants:
        want = wants.pop()
        if want not in candidates:
            raise BuildUnDefined(want)
        ret.add(want)
        for dep in candidates[want].depends_on:
            if dep not in ret:
                wants.add(dep)
    return ret
