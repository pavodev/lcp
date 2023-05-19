import asyncio
import logging
import traceback

from typing import Any

from aiohttp import web

from redis.asyncio.client import PubSub

from .sock import _process_message
from .utils import PUBSUB_CHANNEL


async def handle_redis_response(
    channel: PubSub, app: web.Application, test: bool = False
) -> None:
    """
    If redis publishes a message, it gets picked up here in an async loop
    and broadcast to the correct websockets.

    We need to know if we're running c-compiled code or not, because
    channel.get_message() fails when compiled to c for some reason
    """
    message: Any = None

    try:
        if app.get("mypy", False) is True:
            async for message in channel.listen():
                await _process_message(message, channel, app)
                if message and test is True:
                    return None
        else:
            while True:
                message = await channel.get_message(
                    ignore_subscribe_messages=True, timeout=2.0
                )
                await _process_message(message, channel, app)
                if message and test is True:
                    return None

    except asyncio.TimeoutError as err:
        print(f"Warning: timeout in websocket listener ({err})")
    except asyncio.CancelledError as err:
        tb = traceback.format_exc()
        print(f"Canceled redis handler: {err}\n\n{tb}")
    except Exception as err:
        formed = traceback.format_exc()
        print(f"Error: {str(err)}\n{formed}")
        extra = {"error": str(err), "status": "failed", "traceback": formed}
        logging.error(str(err), extra=extra)


async def listen_to_redis(app: web.Application) -> None:
    """
    Using our async redis connection instance, listen for events coming from redis
    and delegate to the sender
    """
    async with app["aredis"].pubsub() as channel:
        await channel.subscribe(PUBSUB_CHANNEL)
        try:
            await handle_redis_response(channel, app, test=False)
        except KeyboardInterrupt:
            pass
        except Exception as err:
            raise err
        await channel.unsubscribe(PUBSUB_CHANNEL)
        try:
            await app["aredis"].quit()
        except Exception:
            pass
        try:
            await app["redis"].quit()
        except Exception:
            pass
