"""Main script.

This module provides basic CLI entrypoint.

"""
import asyncio
import logging
from enum import Enum
from logging import Logger

import typer
from kilroy_face_server_py_sdk import FaceServer

from kilroy_face_twitter.config import FaceConfig, ServerConfig
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


async def run(
    face_config: FaceConfig, server_config: ServerConfig, logger: Logger
) -> None:
    face = await TwitterFace.build(face_config)
    server = FaceServer(face, logger)
    await server.run(**server_config.dict())


@cli.command()
def main(
    verbosity: Verbosity = typer.Option(
        default="INFO", help="Verbosity level."
    )
) -> None:
    """Command line interface for kilroy-face-twitter."""

    face_config = FaceConfig.build()
    server_config = ServerConfig.build()
    logger = get_logger(verbosity)

    asyncio.run(run(face_config, server_config, logger))


if __name__ == "__main__":
    # entry point for "python -m"
    cli()
