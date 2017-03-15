import datetime
import logging
import subprocess


LOG = logging.getLogger(__name__)
_tag_template_args = None
_label_template_args = None


class TemplateArgsGenerator(object):
    def gen_args(self):
        raise StopIteration
        # yield needed to make gen_args a generator function
        yield


class DateGenerator(TemplateArgsGenerator):
    def gen_args(self):
        yield 'date', datetime.datetime.now().strftime("%Y%m%d")


class ExternalCmdGenerator(TemplateArgsGenerator):
    def __init__(self, key=None, cmd=None):
        self.key = key or self.__class__.key
        self.cmd = cmd or self.__class__.cmd

    def gen_args(self):
        try:
            value = subprocess.check_output(self.cmd,
                                            stderr=subprocess.STDOUT,
                                            shell=not isinstance(self.cmd,
                                                                 list))
            value = value.strip()
            if value:
                yield self.key, value.strip()
        except subprocess.CalledProcessError as e:
            log_level = logging.WARNING

            # having 0 tags is not worthy of warning
            if (isinstance(self, GitDescribeGenerator) and
                    "No names found" in e.output):
                log_level = logging.INFO
            LOG.log(log_level, "failed to run %s: %s", self.cmd, e)
            pass


class GitCommitGenerator(ExternalCmdGenerator):
    key = 'fcommitid'
    cmd = 'git rev-parse HEAD'

    def gen_args(self):
        for k, v in super(GitCommitGenerator, self).gen_args():
            yield k, v
            yield 'scommitid', v[:7]


class GitCommitMsgGenerator(ExternalCmdGenerator):
    key = 'commitmsg'
    cmd = 'git log --oneline|head -1'


class GitBranchGenerator(ExternalCmdGenerator):
    key = 'git_branch'
    cmd = 'git rev-parse --abbrev-ref HEAD'


class GitTagGenerator(ExternalCmdGenerator):
    key = 'git_tag'
    cmd = 'git tag --contains HEAD|head -1'


class GitDescribeGenerator(ExternalCmdGenerator):
    key = 'git_describe'
    cmd = 'git describe --tags'


def _template_args(generators):
    return dict((k, v) for g in generators for k, v in g.gen_args())


def tag_template_args(extra_generators=None):
    global _tag_template_args
    if _tag_template_args is not None:
        return _tag_template_args
    extra_generators = extra_generators or []
    generators = [GitCommitGenerator(), GitCommitMsgGenerator(),
                  GitBranchGenerator(), GitTagGenerator(),
                  GitDescribeGenerator(), DateGenerator()]
    generators.extend(extra_generators)
    _tag_template_args = _template_args(generators)
    return _tag_template_args


def label_template_args(extra_generators=None):
    global _label_template_args
    if _label_template_args is not None:
        return _label_template_args
    extra_generators = extra_generators or []
    generators = [GitCommitGenerator(), GitCommitMsgGenerator(),
                  GitBranchGenerator(), GitTagGenerator(),
                  GitDescribeGenerator()]
    generators.extend(extra_generators)
    _label_template_args = _template_args(generators)
    return _label_template_args
