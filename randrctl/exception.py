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


class ParseException(RandrCtlException):
    """
    Is thrown when randrctl fails to parse some value into a domain object
    """

    def __init__(self, name: str, status: str, state: str):
        Exception.__init__(self, "Failed to parse '{}' for {} {}".format(state, status, name))


class NoSuchProfileException(RandrCtlException):
    """
    Thrown when profile is referred by name, but no such exist
    """

    def __init__(self, name: str, search_locations: list):
        self.name = name
        self.search_locations = search_locations
        Exception.__init__(self, "No profile '{}' found under {}".format(self.name, self.search_locations))


class XrandrException(RandrCtlException):
    """
    is thrown when call to xrandr fails
    """

    def __init__(self, err: str, args: list):
        self.args = args
        Exception.__init__(self, err)
