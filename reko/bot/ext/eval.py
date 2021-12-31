import hikari
import lightbulb
import inspect

eval_plugin = lightbulb.Plugin('Evaluation expressions plugin')

@eval_plugin.command()
@lightbulb.add_checks(lightbulb.owner_only)
@lightbulb.option('expression', 'Выражение для выполнения', hikari.OptionType.STRING)
@lightbulb.command('eval', 'Выполнение выражений', guilds=[913904747625468005])
@lightbulb.implements(lightbulb.SlashCommand)
async def eval_cmd(ctx: lightbulb.Context):
    embed = hikari.Embed(
        title='Выполнение выражения',
        description=f'```py\n{str(ctx.options.expression)}```'
    )
    try:
        res = eval(str(ctx.options.expression))
        
    except Exception as e:
        embed.title = 'Ошибка выражения'
        embed.color = 0xe98d42
        embed.add_field(name='Содержание ошибки', value=e)
        await ctx.respond(embed=embed)
        return


    if inspect.isawaitable(res):
        embed.add_field(name='Возврат', value=await res)
    else:
        embed.add_field(name='Возврат', value=res)
    embed.color = 0x9c76ad
    embed.add_field(name='Тип', value=str(type(res)))

    await ctx.respond(embed=embed)


@eval_plugin.listener(lightbulb.CommandErrorEvent)
async def not_owner(event: lightbulb.CommandErrorEvent):
    exception = event.exception.__cause__ or event.exception
    if isinstance(exception, lightbulb.NotOwner):
        await event.context.respond(
            'Вам нельзя использовать эту команду!!! <:VV:917664230398885930>',
            flags=hikari.MessageFlag.EPHEMERAL
        )


def load(client):
    client.add_plugin(eval_plugin)

def unload(client):
    client.remove_plugin(eval_plugin)