from aiogram.types import BotCommand

BOT_COMMANDS = [
    BotCommand(command="start", description="Почати роботу з ботом"),
    BotCommand(command="films", description="Популярні фільми"),
    BotCommand(command="search", description="Пошук за назвою"),
    BotCommand(command="search_by_genre", description="Пошук за жанром"),
    BotCommand(command="favorites", description="Показати обрані фільми"),
]

async def setup_commands(bot):
    await bot.set_my_commands(BOT_COMMANDS)
