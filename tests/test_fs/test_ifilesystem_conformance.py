"""Tests that the built-in backends conform to the IFileSystem Protocol.

The Protocol is what a custom backend is written against, so anything the
interpreter or a command calls unconditionally has to be declared on it, and
every built-in backend has to implement everything it declares.
"""

import inspect
import pytest

from just_bash.fs import InMemoryFs, MountableFs, OverlayFs, ReadWriteFs
from just_bash.types import IFileSystem

BACKENDS = [InMemoryFs, MountableFs, OverlayFs, ReadWriteFs]

PROTOCOL_METHODS = sorted(
    name
    for name, member in vars(IFileSystem).items()
    if not name.startswith("_") and inspect.isfunction(member)
)

# Gaps that predate this test, listed so it can still guard everything else.
# realpath() is declared on IFileSystem but only InMemoryFs implements it, so
# `pwd -P` and `readlink -f` raise AttributeError on the other three backends.
# Removing an entry here once the backend implements it keeps the test passing.
KNOWN_GAPS = {
    (MountableFs, "realpath"),
    (OverlayFs, "realpath"),
    (ReadWriteFs, "realpath"),
}


def _expected(backend) -> list[str]:
    """Protocol methods the backend is expected to have."""
    return [n for n in PROTOCOL_METHODS if (backend, n) not in KNOWN_GAPS]


class TestProtocolCoverage:
    """Test that the Protocol declares what the commands call."""

    @pytest.mark.parametrize(
        "name,caller",
        [
            ("cp", "cp"),
            ("mv", "mv"),
            ("link", "ln"),
            ("lstat", "readlink, test -L"),
        ],
    )
    def test_declares_method_used_by_commands(self, name, caller):
        """Methods called without a hasattr guard should be declared."""
        assert name in PROTOCOL_METHODS, f"{caller} calls fs.{name}() but IFileSystem omits it"


class TestBackendConformance:
    """Test that every built-in backend implements the Protocol."""

    @pytest.mark.parametrize("backend", BACKENDS, ids=lambda b: b.__name__)
    def test_implements_every_method(self, backend):
        """Backend should have every method the Protocol declares."""
        missing = [n for n in _expected(backend) if not callable(getattr(backend, n, None))]
        assert not missing, f"{backend.__name__} is missing: {', '.join(missing)}"

    @pytest.mark.parametrize("backend", BACKENDS, ids=lambda b: b.__name__)
    def test_async_methods_are_coroutines(self, backend):
        """A method declared async should be a coroutine function on the backend."""
        mismatched = [
            n
            for n in _expected(backend)
            if inspect.iscoroutinefunction(getattr(IFileSystem, n))
            != inspect.iscoroutinefunction(getattr(backend, n, None))
        ]
        assert not mismatched, f"{backend.__name__} does not match on: {', '.join(mismatched)}"
