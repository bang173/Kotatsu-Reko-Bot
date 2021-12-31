import lightbulb
import hikari
from reko.bot import __version__ as reko_version


other_cmds_plugin = lightbulb.Plugin('Other Commands')

@other_cmds_plugin.command()
@lightbulb.command('credits', 'Показывает информацию о боте', guilds=[913904747625468005])
@lightbulb.implements(lightbulb.SlashCommand)
async def credits(ctx: lightbulb.Context):
    embed = hikari.Embed(
        title='Информация',
        description=f'Reko написана на Python 3.9.7, hikari {hikari.__version__} + lightbulb {lightbulb.__version__}',
        color=0x89ffa1
    )
    embed.add_field(name='Версия бота', value=reko_version)
    embed.add_field(name='Разработчик', value=ctx.get_guild().get_member(616691484057534465))
    await ctx.respond(embed=embed)


# @other_cmds_plugin.command()
# @lightbulb.command('rekotest', 'что', guilds=[913904747625468005])
# @lightbulb.implements(SlashCommand)



def load(client):
    client.add_plugin(other_cmds_plugin)

def unload(client):
    client.remove_plugin(other_cmds_plugin)