import logging
from enum import Enum

import typer


class Verbosity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TyperLoggerHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        fg = None
        bg = None
        if record.levelno == logging.DEBUG:
            fg = typer.colors.BLACK
        elif record.levelno == logging.INFO:
            fg = typer.colors.BLUE
        elif record.levelno == logging.WARNING:
            fg = typer.colors.YELLOW
        elif record.levelno == logging.CRITICAL:
            fg = typer.colors.RED
        elif record.levelno == logging.ERROR:
            fg = typer.colors.RED
        typer.secho(self.format(record), bg=bg, fg=fg)


def configure(verbosity) -> None:
    logging.basicConfig(
        format="%(levelname)s\t%(message)s",
        level=verbosity.value,
        handlers=[TyperLoggerHandler()],
    )
