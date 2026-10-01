"""
Spec §6: 'Meaningful error messages ... without exposing internal stack
traces to end users.' Every exception here carries a message that is already
safe to show as-is — handlers.py's job is just to pick the right HTTP status,
never to rewrite the text.
"""


class ReportBuilderError(Exception):
    """Base class — catch this in handlers.py to guarantee nothing unhandled leaks."""

    status_code: int = 400


class AuthenticationError(ReportBuilderError):
    status_code = 401


class SchemaError(ReportBuilderError):
    """Table/column not found, reflection failed, etc."""

    status_code = 404


class UnknownIdentifierError(SchemaError):
    pass


class CompileError(ReportBuilderError):
    """Something about the report request couldn't be turned into valid SQL."""

    status_code = 422


class ReadOnlyViolationError(ReportBuilderError):
    status_code = 403


class UnsupportedJoinTypeError(CompileError):
    pass


class ConnectionTimeoutError(ReportBuilderError):
    status_code = 504


class TemplateNotFoundError(ReportBuilderError):
    status_code = 404
