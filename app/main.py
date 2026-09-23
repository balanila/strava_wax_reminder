from __future__ import annotations

import asyncio
import logging

from app.bot import build_application, send_alert
from app.config import Config
from app.service import ChainWaxService
from app.state import StateStore
from app.strava import StravaClient


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def main() -> None:
    configure_logging()
    config = Config.from_env()
    state_store = StateStore(config.state_path, config.default_interval_km)
    state_store.load()
    strava_client = StravaClient(config=config, state_store=state_store)
    service = ChainWaxService(
        state_store=state_store,
        strava_client=strava_client,
        timezone=config.timezone,
        check_time=config.check_time,
    )
    application = build_application(config, service)
    scheduler_task = asyncio.create_task(
        service.run_daily_scheduler(lambda text: send_alert(application, config.telegram_chat_id, text))
    )

    async with application:
        await application.start()
        await application.updater.start_polling()
        try:
            await asyncio.Event().wait()
        finally:
            scheduler_task.cancel()
            await application.updater.stop()
            await application.stop()


if __name__ == "__main__":
    asyncio.run(main())

