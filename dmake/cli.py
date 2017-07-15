import argparse
import logging

from dmake.errors import *  # noqa
from dmake import utils
from dmake import template_args
import dmake.build

LOG = logging.getLogger(__name__)


def argparser():
    parser = argparse.ArgumentParser(description="build docker images"
                                     " in a simpler way.")
    parser.add_argument('builds', type=str, nargs='*',
                        help='builds to execute.')
    parser.add_argument('-f', '--file', dest='dmakefile',
                        default='.docker-make.yml',
                        help='path to docker-make configuration file.')
    parser.add_argument('-d', '--detailed', default=False,
                        action='store_true', help='print out detailed logs')
    parser.add_argument('-rm', '--remove', default=False,
                        action='store_true',
                        help='remove intermediate containers')
    parser.add_argument('--dry-run', dest='dryrun', action='store_true',
                        default=False, help='print docker commands only')
    parser.add_argument('--no-push', dest='nopush', action='store_true',
                        default=False, help='build only, dont push images.')
    return parser


def _main():
    global LOG

    parser = argparser()
    args = parser.parse_args()

    log_format = '%(levelname)s %(name)s(%(lineno)s) %(asctime)s %(msg)s'
    log_level = logging.DEBUG if args.detailed else logging.INFO
    logging.basicConfig(format=log_format, level=log_level)
    LOG = logging.getLogger("docker-make")

    try:
        template_args.init_tag_names(args.dmakefile)
        builds_order, builds_dict = utils.get_sorted_build_dicts_from_yaml(
            args.dmakefile)
    except ConfigurationError as e:
        LOG.error("failed to parse %s: %s" % (args.dmakefile, e.message))
        return 1
    except ValidateError as e:
        LOG.error("wrong configuration: %s" % e.message)
        return 1
    except DmakeError as e:
        LOG.eror(e.message)
        return 1

    builds = {}
    for name in builds_order:
        if (args.remove):
            builds_dict[name]['remove_intermediate'] = args.remove
        builds[name] = dmake.build.Build(name=name, **builds_dict[name])

    if args.builds:
        try:
            wants = utils.expand_wants(builds, args.builds)
        except BuildUnDefined as e:
            LOG.error("No such build:  %s" % e.build)
            return 1
    else:
        wants = set(builds_order)

    if args.dryrun:
        for name in builds_order:
            if name not in wants:
                continue
            build = builds[name]
            build.dryrun()
        return

    for name in builds_order:
        if name not in wants:
            continue
        build = builds[name]
        if build.rewrite_from:
            build.rewrite_from = builds[build.rewrite_from].non_labeled_image
        try:
            build.build()
            build.tag()
        except BuildFailed as e:
            LOG.error("failed to build %s: %s" % (build.name, e.message))
            return 1
        except Exception:
            LOG.exception("failed to build %s" % build.name)
            return 1

        if not args.nopush:
            try:
                build.push()
            except PushFailed as e:
                LOG.error("failed to push %s: %s" % (build.name, e.message))
                return 1
            except Exception as e:
                LOG.exception("failed to push %s" % build.name)
                return 1


def main():
    try:
        return _main()
    finally:
        utils.GarbageCleaner.clean_all()
