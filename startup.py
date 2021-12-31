import os
import hikari

import reko

reko_activity = hikari.Activity(
    name='Привет, я Реко',
    type=hikari.ActivityType.COMPETING
)


if __name__ == '__main__':

    if os.name != "nt":
        import uvloop
        uvloop.install()

    reko = reko.Reko()

    reko.load_extensions(
        'reko.bot.ext.other_cmds',
        'reko.bot.ext.nsfw_cmds',
        'reko.bot.ext.eval',
        'reko.bot.ext.minigame'
        # 'reko.bot.ext.music'
    )
        

    reko.run(
        activity=reko_activity
    )
