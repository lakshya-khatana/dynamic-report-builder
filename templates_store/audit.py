"""
Spec §4: 'Track creation timestamp, last modification timestamp, and author
metadata per template.' The timestamps are handled at the DB layer
(server_default / onupdate in templates_store/models.py) so they can never
be forgotten by a caller — this module is just where author resolution
would plug in once real auth exists.
"""


def resolve_author(request_context: dict | None) -> str | None:
    """
    Placeholder until auth is wired in. Once there's a real user/session,
    this is the one place that changes — nothing in repository.py or the
    API routes should read the author from anywhere else.
    """
    if request_context and "user_email" in request_context:
        return request_context["user_email"]
    return None
