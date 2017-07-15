import re
import datetime
import logging
import subprocess

from dmake import utils


LOG = logging.getLogger(__name__)
TAG_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_][]a-zA-Z0-9_\.\-]{0,127}$')
TAG_NAME_LEAD_PATTERN = re.compile(r'^[a-zA-Z0-9_]$')
TAG_NAME_ELEMENT_PATTERN = re.compile(r'^[a-zA-Z0-9_\.\-]$')
_tag_template_args = None
_label_template_args = None


class TemplateArgsGenerator(object):
    def gen_args(self):
        raise StopIteration
        # yield needed to make gen_args a generator function
        yield


class DateTimeGenerator(TemplateArgsGenerator):
    def __init__(self, name, format):
        self.name = name
        self.format = format

    def gen_args(self):
        yield self.name, datetime.datetime.now().strftime(self.format)


class DateGenerator(DateTimeGenerator):
    def __init__(self):
        super(DateGenerator, self).__init__('date', '%Y%m%d')


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
    result = {}
    for g in generators:
        for k, v in g.gen_args():
            if not validate_tag_name(v):
                result[k] = correct_tag_name(v)
                LOG.warn("%s is not a valid docker tag name,"
                         "will be automatically corrected to %s",
                         v, result[k])
            else:
                result[k] = v
    return result


def validate_tag_name(name):
    return TAG_NAME_PATTERN.match(name) is not None


def correct_tag_name(name):
    if not name:
        return "null"
    tmp_lst = []
    lead, suffix = name[0], name[1:]
    if TAG_NAME_LEAD_PATTERN.match(lead) is None:
        tmp_lst.append('_')
    else:
        tmp_lst.append(lead)

    for c in suffix:
        if TAG_NAME_ELEMENT_PATTERN.match(c) is None:
            tmp_lst.append('_')
        else:
            tmp_lst.append(c)
    return ''.join(tmp_lst)[:128]


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


def init_tag_names(dmakefile):
    data = utils.load_yaml(dmakefile)
    configurations = data.get('tag-names', None)
    extra_generators = create_extra_generators(configurations)
    label_template_args(extra_generators)
    tag_template_args(extra_generators)


def create_extra_generators(configurations):
    if configurations is None:
        return []

    configurable_tag_name_generators = {
        'datetime': DateTimeGenerator,
        'cmd': ExternalCmdGenerator
    }

    tag_name_generators = []

    for config in configurations:
        if not validate_tag_name_config(config):
            continue
        name, type_, value = config['name'], config['type'], config['value']
        cls = configurable_tag_name_generators.get(type_, None)
        if cls is not None:
            tag_name_generators.append(cls(name, value))
    return tag_name_generators


def validate_tag_name_config(config):
    for key in ('name', 'type', 'value'):
        if key not in config:
            LOG.warn("%s absent in %s", key, config)
            return False
    return True
