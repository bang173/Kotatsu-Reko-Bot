import os
import hikari

import reko

# Configures
chat_id = 913906370770776104
join_asset = 'reko/assets/join.jpg'
me = 616691484057534465

reko_activity = hikari.Activity(
    name='Привет, я Реко',
    type=hikari.ActivityType.COMPETING
)


if __name__ == '__main__':

    if os.name != "nt":
        import uvloop
        uvloop.install()

    reko = reko.Reko()

    # @rekobot.listen(hikari.MemberCreateEvent)
    # async def on_member_join(event: hikari.MemberCreateEvent):
    #     channel = event.get_guild().get_channel(chat_id)
    #     member_count = event.get_guild().member_count
    #     embed = hikari.Embed(
    #         title='Добро пожаловать!',
    #         description='Не стесняйся, присаживайся к нам за наш котацу. 🍡'
    #                     f'\nНас уже целых {member_count}!',
    #         color=0xffe689
    #     )
    #     embed.set_image(join_asset)
    #     await channel.send(
    #         content=event.member.mention,
    #         embed=embed,
    #         user_mentions=[event.member.user]
    #     )

    # @rekobot.listen(hikari.GuildMessageCreateEvent)
    # async def on_member_join_test(event: hikari.GuildMessageCreateEvent):
    #     if event.content.startswith('reko test') and event.member.id == me:
    #         channel = event.get_guild().get_channel(chat_id)
    #         member_count = event.get_guild().member_count
    #         embed = hikari.Embed(
    #             title='Добро пожаловать!',
    #             description='Не стесняйся, присаживайся к нам за наш котацу. 🍡'
    #                         f'\nНас уже целых {member_count}!',
    #             color=0xffe689
    #         )

    #         embed.set_image(join_asset)
    #         # embed.set_thumbnail(event.member.ava)
    #         await channel.send(
    #             content=event.member.mention,
    #             embed=embed,
    #             user_mentions=[event.member.user]
    #         )

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