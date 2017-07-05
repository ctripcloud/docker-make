import subprocess
from datetime import datetime

import unittest2
from mock import mock

from dmake import template_args


class TemplateArgsGeneratorTests(unittest2.TestCase):
    @mock.patch('datetime.datetime')
    def test_date_generator(self, mocked_datetime):
        mocked_datetime.now.return_value = datetime(2016, 7, 21)
        args_date = next(template_args.DateGenerator().gen_args(), None)
        self.assertIsInstance(args_date, tuple)
        k, v = args_date
        self.assertEqual(k, 'date')
        self.assertEqual(v, '20160721')
        mocked_datetime.now.assert_called_once()

    @mock.patch('datetime.datetime')
    def test_datetime_generator(self, mocked_datetime):
        mocked_datetime.now.return_value = datetime(2016, 7, 21, 12, 23)
        args_date = next(template_args.DateTimeGenerator(
            'datetime', '%Y%m%d%H%M').gen_args(), None)
        self.assertIsInstance(args_date, tuple)
        k, v = args_date
        self.assertEqual(k, 'datetime')
        self.assertEqual(v, '201607211223')
        mocked_datetime.now.assert_called_once()


class ExternalCmdGeneratorTests(unittest2.TestCase):

    @mock.patch('subprocess.check_output', return_value=' dummy ')
    def test_key_cmd_in_cls_attr(self, mocked_check_output):
        class DummyGenerator(template_args.ExternalCmdGenerator):
            key = 'dummy'
            cmd = 'echo dummy'
        args = next(DummyGenerator().gen_args(), None)
        self.assertIsInstance(args, tuple)
        k, v = args
        self.assertEqual(k, 'dummy')
        self.assertEqual(v, 'dummy')
        mocked_check_output.assert_called_once_with('echo dummy', shell=True, stderr=-2)

    @mock.patch('subprocess.check_output', return_value=' dummy ')
    def test_key_cmd_in_init(self, mocked_check_output):
        key, cmd = 'dummy', 'echo dummy'
        args = next(template_args.ExternalCmdGenerator(key, cmd).gen_args(), None)
        self.assertIsInstance(args, tuple)
        k, v = args
        self.assertEqual(k, 'dummy')
        self.assertEqual(v, 'dummy')
        mocked_check_output.assert_called_once_with('echo dummy', shell=True, stderr=-2)

    @mock.patch('subprocess.check_output', side_effect=subprocess.CalledProcessError(-1, 'echo dummy'))
    def test_raise_call_error(self, mocked_check_output):
        key, cmd = 'dummy', 'echo dummy'
        args = next(template_args.ExternalCmdGenerator(key, cmd).gen_args(), None)
        self.assertIsNone(args)
        mocked_check_output.assert_called_once_with('echo dummy', shell=True, stderr=-2)

    @mock.patch('subprocess.check_output', return_value=' ')
    def test_blank_output(self, mocked_check_output):
        key, cmd = 'dummy', 'echo dummy'
        args = next(template_args.ExternalCmdGenerator(key, cmd).gen_args(), None)
        self.assertIsNone(args)
        mocked_check_output.assert_called_once_with('echo dummy', shell=True, stderr=-2)


class GitGeneratorsTests(unittest2.TestCase):
    @mock.patch('subprocess.check_output', return_value='56903369fd200ea021dbb75f357f94b7fb5e829e')
    def test_git_commit(self, mocked_check_output):
        pairs = template_args.GitCommitGenerator().gen_args()
        k1, v1 = next(pairs)
        self.assertEqual(k1, 'fcommitid')
        self.assertEqual(v1, '56903369fd200ea021dbb75f357f94b7fb5e829e')
        mocked_check_output.assert_called_once_with('git rev-parse HEAD', shell=True, stderr=-2)

        k2, v2 = next(pairs)
        self.assertEqual(k2, 'scommitid')
        self.assertEqual(v2, '5690336')

    @mock.patch('subprocess.check_output', return_value='5690336 refactor and add unit tests.')
    def test_git_commitmsg(self, mocked_check_output):
        k, v = next(template_args.GitCommitMsgGenerator().gen_args())
        self.assertEqual(k, 'commitmsg')
        self.assertEqual(v, '5690336 refactor and add unit tests.')
        mocked_check_output.assert_called_once_with('git log --oneline|head -1', shell=True,
                                                    stderr=-2)

    @mock.patch('subprocess.check_output', return_value='master')
    def test_git_branch(self, mocked_check_output):
        k, v = next(template_args.GitBranchGenerator().gen_args())
        self.assertEqual(k, 'git_branch')
        self.assertEqual(v, 'master')
        mocked_check_output.assert_called_once_with('git rev-parse --abbrev-ref HEAD', shell=True,
                                                    stderr=-2)

    @mock.patch('subprocess.check_output', return_value='1.11.3')
    def test_git_tag(self, mocked_check_output):
        k, v = next(template_args.GitTagGenerator().gen_args())
        self.assertEqual(k, 'git_tag')
        self.assertEqual(v, '1.11.3')
        mocked_check_output.assert_called_once_with('git tag --contains HEAD|head -1', shell=True,
                                                    stderr=-2)

    @mock.patch('subprocess.check_output', return_value='1.1.2-5-g5690336')
    def test_git_describe(self, mocked_check_output):
        k, v = next(template_args.GitDescribeGenerator().gen_args())
        self.assertEqual(k, 'git_describe')
        self.assertEqual(v, '1.1.2-5-g5690336')
        mocked_check_output.assert_called_once_with('git describe --tags', shell=True, stderr=-2)


class ArgsExportingFunctionTests(unittest2.TestCase):
    @mock.patch('datetime.datetime')
    def test__template_args(self, mocked_datetime):
        mocked_datetime.now.return_value = datetime(2016, 7, 21)
        generators = [template_args.DateGenerator()]
        ret = template_args._template_args(generators)
        self.assertEqual(ret, {'date': '20160721'})
        mocked_datetime.now.assert_called_once()

    @mock.patch('dmake.template_args._template_args', return_value={})
    def test_tag_template_args(self, mocked__template_args):
        self.assertIsNone(template_args._tag_template_args)
        ret = template_args.tag_template_args()
        self.assertEqual(ret, {})
        self.assertEqual(template_args._tag_template_args, {})
        ta = template_args
        generator_classes = [ta.GitCommitGenerator, ta.GitCommitMsgGenerator,
                             ta.GitBranchGenerator, ta.GitTagGenerator,
                             ta.GitDescribeGenerator, ta.DateGenerator]
        for obj, cls in zip(mocked__template_args.call_args[0][0],
                            generator_classes):
            self.assertIsInstance(obj, cls)

    @mock.patch('dmake.template_args._template_args', return_value={})
    def test_label_template_args(self, mocked__template_args):
        self.assertIsNone(template_args._label_template_args)
        ret = template_args.label_template_args()
        self.assertEqual(ret, {})
        self.assertEqual(template_args._label_template_args, {})
        ta = template_args
        generator_classes = [ta.GitCommitGenerator, ta.GitCommitMsgGenerator,
                             ta.GitBranchGenerator, ta.GitTagGenerator,
                             ta.GitDescribeGenerator]
        for obj, cls in zip(mocked__template_args.call_args[0][0],
                            generator_classes):
            self.assertIsInstance(obj, cls)

    def test_validate_tag_name_config(self):
        func = template_args.validate_tag_name_config
        self.assertTrue(func({
            'type': 'cmd',
            'name': 'dummy',
            'value': 'echo dummt',
        }))
        self.assertFalse(func({
            'name': 'dummy',
            'value': 'echo dummt',
        }))
        self.assertFalse(func({
            'type': 'cmd',
            'value': 'echo dummt',
        }))
        self.assertFalse(func({
            'type': 'cmd',
            'name': 'dummy',
        }))
        self.assertFalse(func({
        }))

    def test_create_extra_generators(self):
        configurations = [
            {'type': 'cmd',
             'name': 'dummy',
             'value': 'echo dummt'},
        ]
        result = template_args.create_extra_generators(configurations)
        self.assertEqual(1, len(result))
        self.assertIsInstance(result[0],
                              template_args.ExternalCmdGenerator)
        configurations = [
            {'type': 'datetime',
             'name': 'time',
             'value': '%H%M'},
            {'type': 'notexist',
             'name': 'dummy',
             'value': 'dummy'}
        ]
        result = template_args.create_extra_generators(configurations)
        self.assertEqual(1, len(result))
        self.assertIsInstance(result[0],
                              template_args.DateTimeGenerator)

    @mock.patch('dmake.utils.load_yaml')
    @mock.patch('dmake.template_args.label_template_args')
    @mock.patch('dmake.template_args.tag_template_args')
    def test_init_tag_names(self, patched_tag_template_args,
                                  patched_label_template_args,
                                  patched_load_yaml):
        patched_load_yaml.return_value = {'tag-names': []}
        template_args.init_tag_names('.docker-make.yml')
        patched_load_yaml.assert_called_once_with('.docker-make.yml')
        patched_label_template_args.assert_called_once_with([])
        patched_tag_template_args.assert_called_once_with([])
