import os
import tempfile
import logging

import json
from docker import utils as docker_utils

from dmake import utils
from dmake import template_args
from dmake.errors import *  # noqa


LOG = logging.getLogger(__name__)


class Build(object):
    def __init__(self, name, context, dockerfile,
                 dockerignore=None, labels=None, depends_on=None,
                 extract=None, pushes=None, rewrite_from=None,
                 remove_intermediate=None):
        self.name = name
        self.context = os.path.join(os.getcwd(), context.lstrip('/'))
        self.dockerfile = dockerfile
        self.dockerignore = dockerignore or []
        if '.dockerignore' not in self.dockerignore:
            self.dockerignore.append('.dockerignore')
        self.depends_on = depends_on or []
        self.rewrite_from = rewrite_from
        self.remove_intermediate = remove_intermediate

        self.collect_pushes(pushes)
        self.collect_labels(labels)
        self.parse_extract(extract)

    @property
    def docker(self):
        return utils.docker_client()

    def collect_pushes(self, pushes):
        self.pushes = []
        push_rules = pushes or []

        for line in push_rules:
            try:
                push_mode, line = line.split('=', 1)
                repo, tag_template = line.rsplit(':', 1)
                self.pushes.append((push_mode, repo, tag_template))
            except ValueError:
                raise ConfigurationError("wrong format for push %s" % line)

    def collect_labels(self, labels=None):
        self.labels = []
        labels = labels or []
        elements = template_args.label_template_args()
        for label_template in labels:
            try:
                key, value = label_template.split('=', 1)
                value = value.format(**elements)
                value = value.replace('"', r'\"')
                self.labels.append('%s="%s"' % (key, value))
            except KeyError:
                LOG.warn('invalid label template: %s' % label_template)
            except ValueError:
                raise ConfigurationError("invalid label template: %s" %
                                         label_template)

    def parse_extract(self, extract=None):
        extract = extract or []
        self.extract = []
        for item in extract:
            try:
                src, dst = item.split(':', 1)
            except ValueError:
                raise ConfigurationError('invalid extract rule: %s' % item)
            self.extract.append({
                'src': src,
                'dst': os.path.join(self.context, dst)
            })

    def dryrun(self):
        command = ["docker", "build", "-f", self.dockerfile]
        for label in self.labels:
            command.extend(["--label", label])
        print "%s: %s" % (self.name, " ".join(command))

    def build(self):
        self._update_progress("building")
        self.non_labeled_image = self._build()

        if self.labels:
            self._update_progress("attaching labels")
            self.final_image = self._attach_labels()
        else:
            self.final_image = self.non_labeled_image
        self._update_progress("build succeed: %s" % self.final_image)

        if self.extract:
            self._update_progress("extracting archives")
            self._extract_contents(self.final_image, self.extract)
            self._update_progress("extracting archives succeed")

    def tag(self):
        template_kwargs = template_args.tag_template_args()
        for push_mode, repo, tag_template in self.pushes:
            need_push = self.need_push(push_mode)
            try:
                tag_name = tag_template.format(**template_kwargs)
                kwargs = {}
                if docker_utils.compare_version('1.22',
                                                self.docker._version) < 0:
                    kwargs['force'] = True
                self.docker.tag(self.final_image, repo, tag_name, **kwargs)
                self._update_progress("tag added: %s:%s" % (repo, tag_name))
            except KeyError as e:
                if need_push:
                    LOG.warn('invalid tag_template for this build: %s' %
                             e.message)

    def push(self):
        template_kwargs = template_args.tag_template_args()
        for push_mode, repo, tag_template in self.pushes:
            need_push = self.need_push(push_mode)
            try:
                tag_name = tag_template.format(**template_kwargs)
            except KeyError:
                if need_push:
                    raise PushFailed("can not get tag name for"
                                     "tag_template: %s" % tag_template)
                continue

            self._update_progress("pushing to %s:%s" % (repo, tag_name))
            self._do_push(repo, tag_name)
            self._update_progress("pushed to %s:%s" % (repo, tag_name))

    def need_push(self, push_mode):
        tag_template_args = template_args.tag_template_args()
        return {
            'always': True,
            'never': False,
            'on_tag': tag_template_args.get('git_tag', False),
            'on_branch:{0}'.format(tag_template_args.get('git_branch',
                                                         '9x43d83')): True
        }.get(push_mode, False)

    def _update_progress(self, progress):
        self.progress = progress
        LOG.info("%s: %s" % (self.name, progress))

    def _extract_contents(self, img, paths):
        temp_container = self.docker.create_container(img, 'true')
        assert 'Id' in temp_container
        try:
            for path in paths:
                src, dst = path['src'], path['dst']
                stream, stat = self.docker.get_archive(temp_container, src)
                with open(dst, 'w') as f:
                    f.write(stream.data)
                utils.GarbageCleaner.register(dst)
        finally:
            self.docker.remove_container(temp_container)

    def _build(self):
        dockerfile = os.path.join(self.context, self.dockerfile)
        dockerignore = os.path.join(self.context, '.dockerignore')
        created_dockerignore = False
        if not os.path.exists(dockerignore):
            with open(dockerignore, 'w') as f:
                f.write("\n".join(self.dockerignore))
                created_dockerignore = True
            utils.GarbageCleaner.register(dockerignore)

        if self.rewrite_from:
            original_lines = open(dockerfile).readlines()
            with open(dockerfile, 'w') as f:
                for line in original_lines:
                    line = line.strip()
                    if line.startswith('FROM'):
                        f.write("FROM %s\n" % self.rewrite_from)
                    else:
                        f.write("%s\n" % line)

        params = {
            'path': self.context,
            'dockerfile': self.dockerfile,
        }

        if self.remove_intermediate:
            LOG.debug("Removing intermediate containers after each build")
            params['rm'] = self.remove_intermediate

        try:
            image_id = self._do_build(params)
        finally:
            if created_dockerignore:
                os.remove(dockerignore)
            if self.rewrite_from:
                with open(dockerfile, 'w') as f:
                    f.write(''.join(original_lines))
        return image_id

    def _attach_labels(self):
        pfile = tempfile.NamedTemporaryFile()
        pfile.write("FROM %s\n" % self.non_labeled_image)
        pfile.write("LABEL %s" % " ".join(self.labels))
        pfile.seek(0)

        params = {
            'fileobj': pfile,
        }

        if self.remove_intermediate:
            LOG.debug("Removing intermediate containers after each build")
            params['rm'] = self.remove_intermediate

        try:
            image_id = self._do_build(params)
        finally:
            pfile.close()
        for label in self.labels:
            self._update_progress("label added: %s" % label)
        return image_id

    def _do_build(self, params):
        response = self.docker.build(**params)
        image_id = None
        for data in response:
            for line in data.splitlines():
                ret = json.loads(line)
                if 'stream' in ret:
                    msg = ret['stream']
                    LOG.debug("%s: %s" % (self.name, msg))
                if 'errorDetail' in ret:
                    raise BuildFailed(ret['errorDetail']['message'])
                if 'Successfully built' in ret.get('stream', ''):
                    image_id = ret['stream'].strip().split()[-1]
        return image_id

    def _do_push(self, repo, tag):
        response = self.docker.push(repo, tag, stream=True)
        for line in response:
            LOG.debug("%s: %s" % (self.name, line))
            if 'errorDetail' in line:
                raise PushFailed("error in push %s:%s: %s" % (repo, tag, line))

    def __repr__(self):
        return "Build: %s(%s)" % (self.name, self.progress)
