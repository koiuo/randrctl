__author__ = 'edio'


class RandrCtlException(Exception):
    """
    Is thrown whenever expected exception occurs inside the app
    """


class ValidationException(RandrCtlException):
    """
    Is thrown when some validation error occurs
    """


