import logging
from typing import Optional

import hikari
import lightbulb

import lavasnek_rs

# If True connect to voice with the hikari gateway instead of lavasnek_rs's
HIKARI_VOICE = True
LAVALINK_PASSWORD = 'yieldcoreL1'
PREFIX = '/'

with open('secrets/token.txt') as f:
    TOKEN = f.read()


class EventHandler:

    async def track_start(self, _: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackStart) -> None:
        logging.info("Трек запущен на сервере: %s", event.guild_id)

    async def track_finish(self, _: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackFinish) -> None:
        logging.info("Трек окончен на сервере: %s", event.guild_id)

    async def track_exception(self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackException) -> None:
        logging.warning("Произошло исключение при воспроизведении на сервере: %d", event.guild_id)

        skip = await lavalink.skip(event.guild_id)
        node = await lavalink.get_guild_node(event.guild_id)

        if not node:
            return

        if skip and not node.queue and not node.now_playing:
            await lavalink.stop(event.guild_id)


plugin = lightbulb.Plugin("Kotatsu Reko Музыкальный плагин")


async def _join(ctx: lightbulb.Context) -> Optional[hikari.Snowflake]:
    assert ctx.guild_id is not None

    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]

    if not voice_state:
        await ctx.respond("Для начала подключитесь к голосому каналу!!")
        return None

    channel_id = voice_state[0].channel_id

    if HIKARI_VOICE:
        assert ctx.guild_id is not None

        await plugin.bot.update_voice_state(ctx.guild_id, channel_id, self_deaf=True)
        connection_info = await plugin.bot.d.lavalink.wait_for_full_connection_info_insert(ctx.guild_id)

    else:
        try:
            connection_info = await plugin.bot.d.lavalink.join(ctx.guild_id, channel_id)
        except TimeoutError:
            await ctx.respond(
                'Не могу подключиться к голосовому каналу почему-то :<'
            )
            return None

    await plugin.bot.d.lavalink.create_session(connection_info)

    return channel_id


@plugin.listener(hikari.ShardReadyEvent)
async def start_lavalink(event: hikari.ShardReadyEvent) -> None:

    builder = (
        lavasnek_rs.LavalinkBuilder(event.my_user.id, TOKEN)
        .set_host("127.0.0.1").set_password(LAVALINK_PASSWORD)
        .set_port(2333)
    )

    if HIKARI_VOICE:
        builder.set_start_gateway(False)

    lava_client = await builder.build(EventHandler())

    plugin.bot.d.lavalink = lava_client


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("join", "Подключиться к текущему голосовому каналу.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def join(ctx: lightbulb.Context) -> None:
    channel_id = await _join(ctx)

    if channel_id:
        await ctx.respond(f"Я зашла в <#{channel_id}>")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("leave", "Выйти из текущего голосового канала и очистить список воспроизведения.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def leave(ctx: lightbulb.Context) -> None:

    await plugin.bot.d.lavalink.destroy(ctx.guild_id)

    if HIKARI_VOICE:
        if ctx.guild_id is not None:
            await plugin.bot.update_voice_state(ctx.guild_id, None)
            await plugin.bot.d.lavalink.wait_for_connection_info_remove(ctx.guild_id)
    else:
        await plugin.bot.d.lavalink.leave(ctx.guild_id)

    await plugin.bot.d.lavalink.remove_guild_node(ctx.guild_id)
    await plugin.bot.d.lavalink.remove_guild_from_loops(ctx.guild_id)

    await ctx.respond("Я покинула голосовой канал :^")


@plugin.command() 
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("query", "Что будем искать?", modifier=lightbulb.OptionModifier.CONSUME_REST)
@lightbulb.command("play", "Поиск по запросу в Ютуб и добавление в список воспроизведения.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def play(ctx: lightbulb.Context) -> None:

    query = ctx.options.query

    if not query:
        await ctx.respond("А что искать?", flags=hikari.MessageFlag.EPHEMERAL)
        return None

    con = plugin.bot.d.lavalink.get_guild_gateway_connection_info(ctx.guild_id)
    if not con:
        await _join(ctx)

    query_information = await plugin.bot.d.lavalink.auto_search_tracks(query)

    if not query_information.tracks: 
        await ctx.respond("Не удалось ничего найти :<")
        return

    try:
        # `.requester()` To set who requested the track, so you can show it on now-playing or queue.
        # `.queue()` To add the track to the queue rather than starting to play the track now.
        await plugin.bot.d.lavalink.play(ctx.guild_id, query_information.tracks[0]).requester(ctx.author.id).queue()
    except lavasnek_rs.NoSessionPresent:
        await ctx.respond(f"Сначала используйте `{PREFIX}join`!")
        return

    await ctx.respond(f"Добавила в список воспроизведения: {query_information.tracks[0].info.title}")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("stop", "Останавливает воспроизведение (skip для возобновления)")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def stop(ctx: lightbulb.Context) -> None:

    await plugin.bot.d.lavalink.stop(ctx.guild_id)
    await ctx.respond("Остановила воспроизведение!")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("skip", "Пропустить текущую музыку")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def skip(ctx: lightbulb.Context) -> None:

    skip = await plugin.bot.d.lavalink.skip(ctx.guild_id)
    node = await plugin.bot.d.lavalink.get_guild_node(ctx.guild_id)

    if not skip:
        await ctx.respond("Что мне пропустить? Сейчас ничего не играет :/")
    else:
        if not node.queue and not node.now_playing:
            await plugin.bot.d.lavalink.stop(ctx.guild_id)

        await ctx.respond(f"Пропущен трек: {skip.track.info.title}")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("pause", "Поставить текущий трек на паузу.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def pause(ctx: lightbulb.Context) -> None:

    await plugin.bot.d.lavalink.pause(ctx.guild_id)
    await ctx.respond("Воспроизведение остановлено!")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("resume", "Продолжить воспроизведение текущего трека.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def resume(ctx: lightbulb.Context) -> None:

    await plugin.bot.d.lavalink.resume(ctx.guild_id)
    await ctx.respond("Воспроизведение восстановлено!")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("nowplaying", "Информация о текущем треке.", aliases=["np"])
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def now_playing(ctx: lightbulb.Context) -> None:

    node = await plugin.bot.d.lavalink.get_guild_node(ctx.guild_id)

    if not node or not node.now_playing:
        await ctx.respond("Сейчас ничего не играет :/")
        return

    # for queue, iterate over `node.queue`, where index 0 is now_playing.
    await ctx.respond(f"Сейчас играет: {node.now_playing.track.info.title}")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.add_checks(lightbulb.owner_only)  # Optional
@lightbulb.option(
    "args", "Аргументы для node", required=False, modifier=lightbulb.OptionModifier.CONSUME_REST
)
@lightbulb.command("data", "Загрузить или прочитать данные из node")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def data(ctx: lightbulb.Context) -> None:
    """Load or read data from the node.
    If just `data` is ran, it will show the current data, but if `data <key> <value>` is ran, it
    will insert that data to the node and display it."""

    node = await plugin.bot.d.lavalink.get_guild_node(ctx.guild_id)

    if not node:
        await ctx.respond("node не найден")
        return None

    if args := ctx.options.args:
        args = args.split(" ")

        if len(args) == 1:
            node.set_data({args[0]: args[0]})
        else:
            node.set_data({args[0]: args[1]})
    await ctx.respond(node.get_data())


if HIKARI_VOICE:

    @plugin.listener(hikari.VoiceStateUpdateEvent)
    async def voice_state_update(event: hikari.VoiceStateUpdateEvent) -> None:
        plugin.bot.d.lavalink.raw_handle_event_voice_state_update(
            event.state.guild_id,
            event.state.user_id,
            event.state.session_id,
            event.state.channel_id,
        )

    @plugin.listener(hikari.VoiceServerUpdateEvent)
    async def voice_server_update(event: hikari.VoiceServerUpdateEvent) -> None:
        await plugin.bot.d.lavalink.raw_handle_event_voice_server_update(event.guild_id, event.endpoint, event.token)


def load(client: lightbulb.BotApp) -> None:
    client.add_plugin(plugin)


def unload(client: lightbulb.BotApp) -> None:
    client.remove_plugin(plugin)