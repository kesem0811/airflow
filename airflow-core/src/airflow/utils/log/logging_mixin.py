#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

import abc
import enum
import logging
import re
import sys
from io import TextIOBase, UnsupportedOperation
from logging import Handler, StreamHandler
from typing import IO, TYPE_CHECKING, Any, TypeVar, cast

if TYPE_CHECKING:
    from logging import Logger

# 7-bit C1 ANSI escape sequences
ANSI_ESCAPE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")


# Private: A sentinel objects
class SetContextPropagate(enum.Enum):
    """
    Sentinel objects for log propagation contexts.

    :meta private:
    """

    # If a `set_context` function wants to _keep_ propagation set on its logger it needs to return this
    # special value.
    MAINTAIN_PROPAGATE = object()
    # Don't use this one anymore!
    DISABLE_PROPAGATE = object()


def __getattr__(name):
    if name in ("DISABLE_PROPOGATE", "DISABLE_PROPAGATE"):
        # Compat for spelling on off chance someone is using this directly
        # And old object that isn't needed anymore
        return SetContextPropagate.DISABLE_PROPAGATE
    raise AttributeError(f"module {__name__} has no attribute {name}")


def remove_escape_codes(text: str) -> str:
    """Remove ANSI escapes codes from string; used to remove "colors" from log messages."""
    return ANSI_ESCAPE.sub("", text)


_T = TypeVar("_T")


class LoggingMixin:
    """Convenience super-class to have a logger configured with the class name."""

    _log: logging.Logger | None = None

    # Parent logger used by this class. It should match one of the loggers defined in the
    # `logging_config_class`. By default, this attribute is used to create the final name of the logger, and
    # will prefix the `_logger_name` with a separating dot.
    _log_config_logger_name: str | None = None

    _logger_name: str | None = None

    def __init__(self, context=None):
        self._set_context(context)
        super().__init__()

    @staticmethod
    def _create_logger_name(
        logged_class: type[_T],
        log_config_logger_name: str | None = None,
        class_logger_name: str | None = None,
    ) -> str:
        """
        Generate a logger name for the given `logged_class`.

        By default, this function returns the `class_logger_name` as logger name. If it is not provided,
        the {class.__module__}.{class.__name__} is returned instead. When a `parent_logger_name` is provided,
        it will prefix the logger name with a separating dot.
        """
        logger_name: str = (
            class_logger_name
            if class_logger_name is not None
            else f"{logged_class.__module__}.{logged_class.__name__}"
        )

        if log_config_logger_name:
            return f"{log_config_logger_name}.{logger_name}" if logger_name else log_config_logger_name
        return logger_name

    @classmethod
    def _get_log(cls, obj: Any, clazz: type[_T]) -> Logger:
        if obj._log is None:
            logger_name: str = cls._create_logger_name(
                logged_class=clazz,
                log_config_logger_name=obj._log_config_logger_name,
                class_logger_name=obj._logger_name,
            )
            obj._log = logging.getLogger(logger_name)
        return obj._log

    @classmethod
    def logger(cls) -> Logger:
        """Return a logger."""
        return LoggingMixin._get_log(cls, cls)

    @property
    def log(self) -> Logger:
        """Return a logger."""
        return LoggingMixin._get_log(self, self.__class__)

    def _set_context(self, context):
        if context is not None:
            set_context(self.log, context)


class ExternalLoggingMixin(metaclass=abc.ABCMeta):
    """Define a log handler based on an external service (e.g. ELK, StackDriver)."""

    @property
    @abc.abstractmethod
    def log_name(self) -> str:
        """Return log name."""

    @abc.abstractmethod
    def get_external_log_url(self, task_instance, try_number) -> str:
        """Return the URL for log visualization in the external service."""

    @property
    @abc.abstractmethod
    def supports_external_link(self) -> bool:
        """Return whether handler is able to support external links."""


# We have to ignore typing errors here because Python I/O classes are a mess, and they do not
# have the same type hierarchy defined as the `typing.IO` - they violate Liskov Substitution Principle
# While it is ok to make your class derive from TextIOBase (and its good thing to do as they provide
# base implementation for IO-implementing classes, it's impossible to make them work with
# IO generics (and apparently it has not even been intended)
# See more: https://giters.com/python/typeshed/issues/6077
class StreamLogWriter(TextIOBase, IO[str]):
    """
    Allows to redirect stdout and stderr to logger.

    :param logger: The logging.Logger instance to write to
    :param level: The log level method to write to, ie. logging.DEBUG, logging.WARNING
    """

    encoding = "undefined"

    @property
    def mode(self):
        return "w"

    @property
    def name(self):
        return f"<logger: {self.logger.name}>"

    def writable(self):
        return True

    def readable(self):
        return False

    def seekable(self):
        return False

    def fileno(self):
        raise UnsupportedOperation("fileno")

    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self._buffer = ""

    def close(self):
        """
        Provide close method, for compatibility with the io.IOBase interface.

        This is a no-op method.
        """

    @property
    def closed(self):
        """
        Return False to indicate that the stream is not closed.

        Streams will be open for the duration of Airflow's lifecycle.

        For compatibility with the io.IOBase interface.
        """
        return False

    def _propagate_log(self, message):
        """Propagate message removing escape codes."""
        self.logger.log(self.level, remove_escape_codes(message))

    def write(self, message):
        """
        Do whatever it takes to actually log the specified logging record.

        :param message: message to log
        """
        if message.endswith("\n"):
            message = message.rstrip()
            self._buffer += message
            self.flush()
        else:
            self._buffer += message

        return len(message)

    def flush(self):
        """Ensure all logging output has been flushed."""
        buf = self._buffer
        if buf:
            self._buffer = ""
            self._propagate_log(buf)

    def isatty(self):
        """
        Return False to indicate the fd is not connected to a tty(-like) device.

        For compatibility reasons.
        """
        return False


class RedirectStdHandler(StreamHandler):
    """
    Custom StreamHandler that uses current sys.stderr/stdout as the stream for logging.

    This class is like a StreamHandler using sys.stderr/stdout, but uses
    whatever sys.stderr/stdout is currently set to rather than the value of
    sys.stderr/stdout at handler construction time, except when running a
    task in a kubernetes executor pod.
    """

    def __init__(self, stream):
        if not isinstance(stream, str):
            raise TypeError(
                "Cannot use file like objects. Use 'stdout' or 'stderr' as a str and without 'ext://'."
            )

        self._use_stderr = True
        if "stdout" in stream:
            self._use_stderr = False
            self._orig_stream = sys.stdout
        else:
            self._orig_stream = sys.stderr
        # StreamHandler tries to set self.stream
        Handler.__init__(self)

    @property
    def stream(self):
        """Returns current stream."""
        from airflow.settings import IS_EXECUTOR_CONTAINER, IS_K8S_EXECUTOR_POD

        if IS_K8S_EXECUTOR_POD or IS_EXECUTOR_CONTAINER:
            return self._orig_stream
        if self._use_stderr:
            return sys.stderr

        return sys.stdout


def set_context(logger, value):
    """
    Walk the tree of loggers and try to set the context for each handler.

    :param logger: logger
    :param value: value to set
    """
    while logger:
        orig_propagate = logger.propagate
        for handler in logger.handlers:
            # Not all handlers need to have context passed in so we ignore
            # the error when handlers do not have set_context defined.

            # Don't use getatrr so we have type checking. And we don't care if handler is actually a
            # FileTaskHandler, it just needs to have a set_context function!
            if hasattr(handler, "set_context"):
                from airflow.utils.log.file_task_handler import FileTaskHandler  # noqa: TC001

                flag = cast("FileTaskHandler", handler).set_context(value)
                # By default we disable propagate once we have configured the logger, unless that handler
                # explicitly asks us to keep it on.
                if flag is not SetContextPropagate.MAINTAIN_PROPAGATE:
                    logger.propagate = False
        if orig_propagate is True:
            # If we were set to propagate before we turned if off, then keep passing set_context up
            logger = logger.parent
        else:
            break
