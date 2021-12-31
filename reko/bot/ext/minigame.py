import asyncio
from typing import List
import hikari
import lightbulb
from localneon import neon
from asyncio import sleep as asleep
# from concurrent.futures import ThreadPoolExecutor
from random import choice, choices, randint
import string


GAME_GUIDE = 'Рекомендую, для участия, всем участникам открыть ЛС. В процессе игры это необходимо.'

GAME_CREATOR_GUIDE = 'Игра создана. Дождитесь сбора игроков и нажмите на кнопку **Начать**. '\
    'После этого начнется игра, при необходимости вы сможете ей управлять.'


pd_plugin = lightbulb.Plugin('Плагин мини-игры "Правда или Действие"')


active_game = None
# {
# <Menu>: List[hikari.User]
# }
pending_games = {}
menu_ids = []
pending_games_by_msg = {}
newest_pending_game_code = None


def generate_id() -> str:
    while True:
        generated = ''.join(
            choices(string.ascii_lowercase + string.digits, k=4))
        if generated not in menu_ids:
            menu_ids.append(generated)
            return generated
        else:
            continue


def get_pending_game(code: str) -> tuple:
    for g, p in pending_games.items():
        if g.id == code:
            return g, p
    return None, None


class MinigameObject:

    __slots__ = 'created_by', 'content'

    def __init__(self, created_by: hikari.User, content: str):
        self.created_by = created_by
        self.content = content

# Правда


class Truth(MinigameObject):

    __slots__ = 'type',

    def __init__(self, *args):
        self.type = 1
        super().__init__(*args)

# Действие


class Action(MinigameObject):

    __slots__ = 'type',

    def __init__(self, *args):
        self.type = 2
        super().__init__(*args)


# Объект самой мини-игры
class Minigame:

    __slots__ = (
        'owner',
        'ctx',
        'players',
        'anon',
        'truth',
        'actions'
    )

    def __init__(self, created_by: hikari.User, context: lightbulb.Context, players_list: List[hikari.User], anonimous: bool):
        self.owner = created_by
        self.ctx = context
        self.players = players_list
        self.anon = anonimous
        self.truth: List[Truth] = list()
        self.actions: List[Action] = list()

    async def __truth_ask(self, player: hikari.User):

        try:
            player_truth_event = await self.ctx.bot.wait_for(
                hikari.DMMessageCreateEvent,
                timeout=180,
                predicate=lambda e: e.author == player and e.message.content
            )
            return player_truth_event.message.content

        except asyncio.TimeoutError:
            await player.send('Прошло уже 3 минуты, а вы мне так и не ответили. Поторопитесь! >:( ')
            await self.ctx.get_channel().send(
                f'{player.mention} что-то задерживается... Дам ему еще 2 минуты..',
                user_mentions=True
            )
            try:
                player_truth_event = await self.ctx.bot.wait_for(
                    hikari.DMMessageCreateEvent,
                    timeout=120,
                    predicate=lambda e: e.author == player and e.message.content
                )
                return player_truth_event.message.content

            except asyncio.TimeoutError:
                await player.send('Время вышло! Я устала ждать!!')
                return None

    async def __action_ask(self, player: hikari.User):
        await player.send('Теперь скажите, какое действие вы бы хотели загадать?')

        try:
            player_action_event = await self.ctx.bot.wait_for(
                hikari.DMMessageCreateEvent,
                timeout=180,
                predicate=lambda e: e.author == player and e.message.content
            )
            return player_action_event.message.content

        except asyncio.TimeoutError:
            await player.send('Прошло уже 3 минуты, а вы мне так и не ответили. Поторопитесь! >:( ')
            await self.ctx.get_channel().send(
                f'{player.mention} что-то задерживается... Дам ему еще 2 минуты..',
                user_mentions=True
            )
            try:
                player_action_event = await self.ctx.bot.wait_for(
                    hikari.DMMessageCreateEvent,
                    timeout=120,
                    predicate=lambda e: e.author == player and e.message.content
                )
                return player_action_event.message.content

            except asyncio.TimeoutError:
                await player.send('Время вышло! Я устала ждать!!')
                return None

    async def _ask(self, player: hikari.User) -> None:

        try:
            await player.send(
                'Привет! Сейчас я у вас спрошу какую бы правду вы хотели узнать и какое действие хотели бы загадать.'
                '\nПожалуйста, не задерживайте других игроков. На ответ у вас есть 3 минуты, в крайнем случае 5 минут.'
                '\nДля начала начнем с правды. Что бы вы хотели узнать?'
            )
        except:
            await self.ctx.get_channel().send(
                f'Не могу написать {player.mention}. Похоже, у этого игрока закрыты ЛС...',
                user_mentions=True
            )
            return

        # Спрашиваем у игрока правду и действие и запоминаем
        player_truth = await self.__truth_ask(player)
        if player_truth:
            self.truth.append(Truth(player, player_truth))

        player_action = await self.__action_ask(player)
        if player_action:
            self.actions.append(Action(player, player_action))

        await player.send(
            'Спасибо! Я запомнила. Возможно ваша правда или ваше действие попадётся победителю в игре)'
        )

    async def start(self) -> None:

        # Функция таймаута интеракций
        def on_timeout():
            global active_game
            active_game = None

        # Определяем локалки
        channel: hikari.TextableChannel = self.ctx.get_channel()
        # это повторение нужно для вложенного класса
        truth = self.truth
        actions = self.actions
        anon = self.anon

        game_start_embed = hikari.Embed(
            title='Игра началась!',
            description=f'Сейчас я расспрошу игроков в следующем порядке: {", ".join([p.mention for p in self.players])}',
            color=0x47ffff
        )

        await channel.send(embed=game_start_embed)

        # Спрашиваем игроков
        for player in self.players:

            msg = await channel.send(f'Спрашиваю игрока {player.mention}', user_mentions=True)
            await self._ask(player)
            await msg.edit(f'Спросила игрока {player.mention}', user_mentions=True)

        # Тянем время
        await asleep(randint(2, 4))

        # Выбираем "победителя" (на самом деле проигравшего)
        winner = choice(self.players)

        # Это менюшка появляется в конце игры
        class EndMenu(neon.ComponentMenu):

            @neon.button('Правда', str(winner.id)+'_1', hikari.ButtonStyle.PRIMARY)
            @neon.button('Действие', str(winner.id)+'_2', hikari.ButtonStyle.PRIMARY)
            @neon.button_group()
            async def end_menu_btns(self, btn: neon.Button):
                # try:

                global active_game
                if active_game:

                    embed = hikari.Embed(
                        color=0x6eabff
                    )
                    if self.inter.user.id == winner.id:
                        if btn.custom_id == str(winner.id)+'_1':
                            print(f'{self.inter.user} pressed правда')
                            final_truth = choice(truth)
                            embed.title = 'Правда'
                            if final_truth:
                                embed.description = final_truth.content
                                if not anon:
                                    embed.set_footer(
                                        text=f'От {final_truth.created_by}')
                            else:
                                embed.description = 'Никто не указал правду, мне не из чего выбирать <:A_HuBlankie:917162201184350298>'

                            await channel.send(embed=embed)
                            active_game = None

                        elif btn.custom_id == str(winner.id)+'_2':
                            print(f'{self.inter.user} pressed действие')
                            final_action = choice(actions)
                            embed.title = 'Действие'
                            if final_action:
                                embed.description = final_action.content
                                if not anon:
                                    embed.set_footer(
                                        text=f'От {final_action.created_by}')
                            else:
                                embed.description = 'Никто не указал действие, мне не из чего выбирать <:A_HuBlankie:917162201184350298>'

                            await channel.send(embed=embed)
                            active_game = None

                    else:
                        await self.inter.create_initial_response(
                            response_type=hikari.ResponseType.MESSAGE_CREATE,
                            content='Только победитель в игре может выбирать!!',
                            flags=hikari.MessageFlag.EPHEMERAL
                        )
                        return

                # except Exception as e:
                #     print(e)

        end_menu = EndMenu(self.ctx, timeout=300, author_only=False)
        end_menu.timeout_func = on_timeout

        end_embed = hikari.Embed(
            title='Правда или действие?',
            description=f'Выбирай, наш несчастный победитель в фортуне {winner.mention}({winner}) <:A_HuTaoPat:917161967779729519>',
            color=0x706eff
        )

        msg = await channel.send(winner.mention, embed=end_embed, components=end_menu.build(), user_mentions=True)

        await end_menu.run(msg)


@pd_plugin.command()
@lightbulb.option('min_players', 'Минимальное кол-во игроков которое может принять участие (от 3 до 5)', hikari.OptionType.INTEGER)
@lightbulb.option('anonimous', 'Анонимные правда или действия или нет (False - нет, True - да)', hikari.OptionType.BOOLEAN)
@lightbulb.command('pd', 'Начать мини-игру "Правда или Действие"', guilds=[913904747625468005])
@lightbulb.implements(lightbulb.SlashCommand)
async def pd(ctx: lightbulb.SlashContext):
    if not active_game:

        if ctx.options.min_players not in (3, 4, 5):
            await ctx.respond(
                'Минимальное количество игрков в игре может быть от 3 до 5!! <:e57:923626646488121344>',
                flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        # try:

        players = [ctx.author]

        await ctx.respond(
            GAME_CREATOR_GUIDE,
            flags=hikari.MessageFlag.EPHEMERAL
        )

        await ctx.get_channel().send(GAME_GUIDE)

        embed = hikari.Embed(
            title='Ожидание игроков',
            description='Используя команду `/pdjoin` и код можно войти в игру! <:A_HuWinky:917161943947698266>',
            color=0x47ffff
        )

        start_game_message: hikari.Message = await ctx.get_channel().send(embed=embed)

        class GameMenu(neon.ComponentMenu):

            def __init__(self, id_, **kwargs):
                self.id: str = id_
                super().__init__(**kwargs)

            @neon.button('Начать', str(start_game_message.id)+'_1', hikari.ButtonStyle.SUCCESS)
            @neon.button('Отмена', str(start_game_message.id)+'_2', hikari.ButtonStyle.SECONDARY)
            @neon.button_group()
            async def menu_btns(self, btn: neon.Button):

                if btn.custom_id == str(start_game_message.id)+'_1':

                    if len(pending_games[self]) >= ctx.options.min_players:

                        global active_game
                        global newest_pending_game_code

                        if not active_game:
                            # Отключаем кнопки
                            components = self.build_components(
                                disabled=True)
                            await self.edit_msg(components=components)

                            # Записываем в глобал активную игру
                            active_game = Minigame(
                                ctx.author, ctx, players, ctx.options.anonimous)

                            # Очистка данных об ожидании
                            pending_games.pop(self)
                            pending_games_by_msg.pop(self.id)
                            menu_ids.remove(self.id)
                            if self.id == newest_pending_game_code:
                                newest_pending_game_code = None

                            # Начинаем игру
                            await active_game.start()

                        else:
                            await ctx.respond(
                                'Сейчас проходит другая игра!! <a:KRAwooo:921665704992866314>',
                                flags=hikari.MessageFlag.EPHEMERAL
                            )

                    else:
                        await ctx.respond(
                            'Не могу начать игру. Недостаточно игроков :<',
                            flags=hikari.MessageFlag.EPHEMERAL
                        )

                elif btn.custom_id == str(start_game_message.id)+'_2':

                    await start_game_message.delete()

                    pending_games.pop(self)
                    pending_games_by_msg.pop(self.id)
                    menu_ids.remove(self.id)
                    if self.id == newest_pending_game_code:
                        newest_pending_game_code = None

                    return

        code = generate_id()
        menu = GameMenu(code, context=ctx, timeout=300, author_only=True)

        # При таймауте кнопок очищаем данные об ожидании
        def on_timeout():
            global newest_pending_game_code

            pending_games.pop(menu)
            pending_games_by_msg.pop(menu.id)
            menu_ids.remove(menu.id)
            if menu.id == newest_pending_game_code:
                newest_pending_game_code = None

        menu.timeout_func = on_timeout

        msg = await start_game_message.edit(components=menu.build())

        pending_games.update({menu: players})
        pending_games_by_msg.update({code: msg})

        global newest_pending_game_code
        newest_pending_game_code = code

        embed.add_field(name='Код', value=code)
        embed.add_field(name='Игроки', value=', '.join(
            [p.mention for p in players]))
        await start_game_message.edit(embed=embed)

        await menu.run(msg)

        # except Exception as e:
        #     print(e)

    else:
        await ctx.respond(
            'Сейчас проходит другая игра! Дождитесь ее окончания! <:VV:917664230398885930>',
            flags=hikari.MessageFlag.EPHEMERAL
        )


@pd_plugin.command()
@lightbulb.option('code', 'Код для входа в мини-игру "Правда или Действие (необязательно)"', hikari.OptionType.STRING, required=False)
@lightbulb.command('pdjoin', 'Войти в мини-игру "Правда или Действие"', guilds=[913904747625468005])
@lightbulb.implements(lightbulb.SlashCommand)
async def pdjoin(ctx: lightbulb.SlashContext):
    # try:

    passed_code = newest_pending_game_code if not ctx.options.code else ctx.options.code

    pending_game_menu, players = get_pending_game(passed_code)

    if not pending_game_menu:
        await ctx.respond(
            'Игра не найдена! Проверьте написание кода и попробуйте еще раз!! <a:tuts:921665568262737920>',
            flags=hikari.MessageFlag.EPHEMERAL
        )
        return
    elif len(players) >= 5:
        await ctx.respond(
            'Игра переполнена!',
            flags=hikari.MessageFlag.EPHEMERAL
        )
        return
    elif ctx.author in players:
        await ctx.respond(
            'Вы уже вошли в эту игру!! <:e57:923626646488121344>',
            flags=hikari.MessageFlag.EPHEMERAL
        )
        return

    else:

        pending_games[pending_game_menu].append(ctx.author)

        embed = hikari.Embed(
            title='Ожидание игроков',
            description='Используя команду `/pdjoin` и код можно войти в игру! <:A_HuWinky:917161943947698266>',
            color=0x47ffff
        )
        embed.add_field(name='Код', value=passed_code)
        embed.add_field(name='Игроки', value=', '.join(
            [p.mention for p in pending_games[pending_game_menu]]))

        await pending_games_by_msg[passed_code].edit(embed=embed)

        class CancelMenu(neon.ComponentMenu):

            @neon.button('Отменить вход', str(pending_games_by_msg[passed_code].id)+'_1', style=hikari.ButtonStyle.DANGER)
            async def cancel_join(self, btn: neon.Button):
                if btn.custom_id == str(pending_games_by_msg[passed_code].id)+'_1':

                    pending_games[pending_game_menu].remove(ctx.author)

                    await pending_games_by_msg[passed_code].edit(embed=embed)

        cancel_menu = CancelMenu(
            context=ctx, timeout=180, author_only=True, disable_on_one_click=True)

        res = await ctx.respond(
            'Вы успешно вошли в игру! <:A_HuWinky:917161943947698266>',
            flags=hikari.MessageFlag.EPHEMERAL,
            components=cancel_menu.build()
        )
        await cancel_menu.run(res)

    # except Exception as e:
    #     print(e)


def load(client):
    client.add_plugin(pd_plugin)


def unload(client):
    client.remove_plugin(pd_plugin)
