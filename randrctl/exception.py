__author__ = 'edio'


class RandrCtlException(Exception):
    """
    Is thrown whenever expected exception occurs inside the app
    """


class ValidationException(RandrCtlException):
    """
    Is thrown when some validation error occurs
    """


class InvalidProfileException(RandrCtlException):
    """
    Is thrown when profile is invalid
    """
    def __init__(self, profile_path: str):
        self.profile_path = profile_path
        Exception.__init__(self, "Invalid profile {}".format(profile_path))
