"""Backward-compatible wrapper for legacy imports."""

from k6.service import K6Service


class K6Logic(K6Service):
    pass
