class DmakeError(Exception):
    pass


class ConfigurationError(DmakeError):
    pass


class ValidateError(DmakeError):
    pass


class DependencyError(DmakeError):
    pass


class BuildFailed(DmakeError):
    pass


class PushFailed(DmakeError):
    pass


class BuildUnDefined(DmakeError):
    def __init__(self, build):
        self.build = build
        super(BuildUnDefined, self).__init__()
