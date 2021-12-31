from __future__ import annotations

from pathlib import Path

import hikari
import lightbulb
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import utc


class Reko(lightbulb.BotApp):

    """Kotatsu Reko bot class"""

    def __init__(self) -> None:
        self._plugins = [p.stem for p in Path('.').glob('./reko/bot/ext/*.py')]
        self.scheduler = AsyncIOScheduler()
        self.scheduler.configure(timezone=utc)

        with open('secrets/token.txt') as f:
            token = f.read()

        super().__init__(
            token=token,
            intents=hikari.Intents.ALL,
            ignore_bots=True,
            owner_ids=[616691484057534465],
            prefix='reko ',
            help_class=None
        )

        