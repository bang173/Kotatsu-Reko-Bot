from hikari.colors import Color
import lightbulb
import hikari
import nekos


nsfw_cmds_plugin = lightbulb.Plugin('Other Commands')


possible = [
    'feet', 'yuri', 'trap', 'futanari', 'hololewd', 'lewdkemo',
    'solog', 'feetg', 'cum', 'erokemo', 'les', 'wallpaper', 'lewdk',
    'ngif', 'tickle', 'lewd', 'feed', 'gecg', 'eroyuri', 'eron',
    'cum_jpg', 'bj', 'nsfw_neko_gif', 'solo', 'kemonomimi', 'nsfw_avatar',
    'gasm', 'poke', 'anal', 'slap', 'hentai', 'avatar', 'erofeet', 'holo',
    'keta', 'blowjob', 'pussy', 'tits', 'holoero', 'lizard', 'pussy_jpg',
    'pwankg', 'classic', 'kuni', 'waifu', 'pat', '8ball', 'kiss', 'femdom',
    'neko', 'spank', 'cuddle', 'erok', 'fox_girl', 'boobs', 'random_hentai_gif',
    'smallboobs', 'hug', 'ero', 'smug', 'goose', 'baka', 'woof'
]

@nsfw_cmds_plugin.command()
@lightbulb.command('cat', 'Отправить котика (Доступно только в канале для медиа)', guilds=[913904747625468005])
@lightbulb.implements(lightbulb.SlashCommand)
async def cat(ctx: lightbulb.Context):
    if ctx.get_channel().id == 915326689821749296:
        await ctx.respond(nekos.cat())


@nsfw_cmds_plugin.command()
@lightbulb.option('tag', 'Выберите тег, с которым искать', hikari.OptionType.STRING)
@lightbulb.command('nneko', 'NSFW Команда', guilds=[913904747625468005])
@lightbulb.implements(lightbulb.SlashCommand)
async def nneko(ctx: lightbulb.Context):
    if ctx.get_channel().is_nsfw:
        if ctx.options.tag in possible:
            await ctx.respond(nekos.img(target=ctx.options.tag))
        else:
            await ctx.respond(
                'Неизвестный тег! Доступные теги можно посмотреть используя команду `/nsfwtags`',
                flags=hikari.MessageFlag.EPHEMERAL
            )
    else:
        await ctx.respond(
            'Нельзя использовать NSFW команды в непредназначенных для этого каналах <a:angry_cutie4:921665783162077224>',
            flags=hikari.MessageFlag.EPHEMERAL
        )


@nsfw_cmds_plugin.command()
@lightbulb.command('nsfwtags', 'NSFW Команда', guilds=[913904747625468005])
@lightbulb.implements(lightbulb.SlashCommand)
async def nsfwtags(ctx: lightbulb.Context):
    if ctx.get_channel().is_nsfw:
        embed = hikari.Embed(
            title='Доступные NSFW теги',
            description=', '.join([f'`{t}`' for t in possible]),
            color=0xff61c0
        )
        await ctx.respond(embed=embed)
        
    else:
        await ctx.respond(
            'Нельзя использовать NSFW команды в непредназначенных для этого каналах <a:angry_cutie4:921665783162077224>',
            flags=hikari.MessageFlag.EPHEMERAL
        )



# hikari.CommandInteraction.create_initial_response()

def load(client):
    client.add_plugin(nsfw_cmds_plugin)

def unload(client):
    client.remove_plugin(nsfw_cmds_plugin)