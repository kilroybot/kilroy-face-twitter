"""Main script.

This module provides basic CLI entrypoint.

"""
import asyncio
import logging
import signal
from asyncio import FIRST_EXCEPTION
from pathlib import Path
from typing import List, Optional

import typer
from typer import FileText

from kilroy_face_server_py_sdk import FaceServer, FaceService
from kilroy_face_twitter import log
from kilroy_face_twitter.config import Config, get_config
from kilroy_face_twitter.face import TwitterFace

cli = typer.Typer()  # this is actually callable and thus can be an entry point

logger = logging.getLogger(__name__)


async def shutdown(sig: signal.Signals, loop: asyncio.AbstractEventLoop):
    loop.remove_signal_handler(sig)
    logger.info(f"Received exit signal {sig.name}...")
    tasks = [
        task
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task()
    ]
    logger.info(f"Cancelling {len(tasks)} outstanding tasks...")
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def attach_signal_handlers() -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )


async def load_or_init(face: TwitterFace, state_dir: Path) -> None:
    if not state_dir.exists() or not any(state_dir.iterdir()):
        logger.info("Initializing face...")
        await face.init()
        logger.info("Initialization complete.")
        return

    try:
        logger.info("Loading state...")
        await face.load_saved(state_dir)
        logger.info("Loading complete.")
    except Exception as e:
        logger.warning(
            "Can't load saved state. Will try to initialize instead.",
            exc_info=e,
        )
        logger.info("Initializing face...")
        await face.init()
        logger.info("Initialization complete.")


async def run(config: Config) -> None:
    await attach_signal_handlers()

    face_type = config.face_type
    state_dir = config.state_directory / face_type

    face_cls = TwitterFace.for_category(face_type)
    face = await face_cls.build(**config.face.dict())
    service = FaceService(face, state_dir)
    server = FaceServer(service, logger)

    server_task = asyncio.create_task(server.run(**config.server.dict()))
    init_task = asyncio.create_task(load_or_init(face, state_dir))

    tasks = [server_task, init_task]

    try:
        done, pending = await asyncio.wait(tasks, return_when=FIRST_EXCEPTION)
    except asyncio.CancelledError:
        done, pending = [], tasks
    except Exception as e:
        logger.warning("Unhandled exception.", exc_info=e)
        done, pending = [], tasks

    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning("Unhandled exception.", exc_info=e)

    for task in done:
        task.result()

    if (
        init_task.done()
        and not init_task.cancelled()
        and init_task.exception() is None
    ):
        logger.info("Saving state...")
        await face.save(state_dir)

        logger.info("Cleaning up...")
        await face.cleanup()


@cli.command()
def main(
    config_file: Optional[FileText] = typer.Option(
        None, "--config-file", "-C", dir_okay=False, help="Configuration file."
    ),
    config: Optional[List[str]] = typer.Option(
        None, "--config", "-c", help="Configuration entries."
    ),
    verbosity: log.Verbosity = typer.Option(
        "INFO", "--verbosity", "-v", help="Verbosity level."
    ),
) -> None:
    """Command line interface for kilroy-face-twitter."""

    log.configure(verbosity)

    logger.info("Loading config...")
    try:
        config = get_config(config_file, config)
    except ValueError as e:
        logger.error("Failed to parse config!", exc_info=e)
        raise typer.Exit(1)
    logger.info("Config loaded!")

    asyncio.run(run(config))


if __name__ == "__main__":
    # entry point for "python -m"
    cli()
