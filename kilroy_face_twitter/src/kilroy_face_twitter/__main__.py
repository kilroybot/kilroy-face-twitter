"""Main script.

This module provides basic CLI entrypoint.

"""
import asyncio
import logging
from asyncio import FIRST_EXCEPTION
from enum import Enum
from logging import Logger
from typing import Dict, Optional

import typer
from kilroy_face_server_py_sdk import FaceServer
from typer import FileText

from kilroy_face_twitter.config import get_config
from kilroy_face_twitter.face import TwitterFace

cli = typer.Typer()  # this is actually callable and thus can be an entry point


class Verbosity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def get_logger(verbosity: Verbosity) -> Logger:
    logging.basicConfig()
    logger = logging.getLogger("kilroy-face-twitter")
    logger.setLevel(verbosity.value)
    return logger


async def run(config: Dict, logger: Logger) -> None:
    face = await TwitterFace.build(**config.get("face", {}))
    server = FaceServer(face, logger)

    tasks = (
        asyncio.create_task(face.init()),
        asyncio.create_task(server.run(**config.get("server", {}))),
    )

    try:
        done, pending = await asyncio.wait(tasks, return_when=FIRST_EXCEPTION)
    except asyncio.CancelledError:
        done, pending = [], tasks

    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    for task in done:
        task.result()

    await face.cleanup()


@cli.command()
def main(
    config: Optional[FileText] = typer.Option(
        default=None, help="Configuration file"
    ),
    verbosity: Verbosity = typer.Option(
        default="INFO", help="Verbosity level."
    ),
) -> None:
    """Command line interface for kilroy-face-twitter."""

    config = get_config(config)
    logger = get_logger(verbosity)

    asyncio.run(run(config, logger))


if __name__ == "__main__":
    # entry point for "python -m"
    cli()
