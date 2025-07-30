import asyncio
import logging
import json
from pathlib import Path

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from data import format_film_details
from external import async_log_function_call
from keyboards import build_films_keyboard, genre_keyboard, build_favorites_keyboard
from commands import setup_commands
from config import TOKEN

ITEMS_PER_PAGE = 5
API_URL = "https://api.imdbapi.dev/titles"
SEARCH_API_URL = "https://api.imdbapi.dev/search/titles"
FAVS_DIR = Path("UserFavorites")
FAVS_DIR.mkdir(exist_ok=True)

bot = Bot(token=TOKEN)
dp = Dispatcher()

class FilmStates(StatesGroup):
    waiting_for_query = State()
    waiting_for_genre = State()

# Старт
@dp.message(CommandStart())
@async_log_function_call
async def cmd_start(message: types.Message):
    await message.answer(
        "Привіт! Я бот IMDb-API бот розроблений @kqudg . Доступні команди:\n"
        "/films - Популярні фільми\n"
        "/search - Пошук за назвою\n"
        "/search_by_genre - Пошук за жанром\n"
        "/favorites - Показати обрані фільми"
    )

# Допоміжні функції для роботи з обраним
def get_favorites_path(user: types.User) -> Path:
    # Використовуємо username якщо є, інакше user_id
    filename = f"{user.username or user.id}.json"
    return FAVS_DIR / filename

def load_favorites(user: types.User) -> list[dict]:
    path = get_favorites_path(user)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Помилка читання файлу обраного {path}: {e}")
            return []
    return []

def save_favorites(user: types.User, favorites: list[dict]):
    path = get_favorites_path(user)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Помилка запису файлу обраного {path}: {e}")

# Клавіатура для пошуку за літерою
def get_az_keyboard():
    buttons = []
    row = []
    for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        row.append(InlineKeyboardButton(text=char, callback_data=f"letter_{char}"))
        if len(row) == 6:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Ввести вручну", callback_data="manual_input")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# /films
@dp.message(Command("films"))
@async_log_function_call
async def show_popular(message: types.Message, state: FSMContext):
    params_movie = {
        "types": "MOVIE",
        "startYear": 2000,
        "minVoteCount": 1000,
        "minAggregateRating": 5.5,
        "sortBy": "SORT_BY_POPULARITY",
    }
    params_series = {
        "types": "TV_SERIES",
        "startYear": 2000,
        "minVoteCount": 1000,
        "minAggregateRating": 5.5,
        "sortBy": "SORT_BY_POPULARITY",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, params=params_movie) as resp_movie:
                data_movie = await resp_movie.json()
            async with session.get(API_URL, params=params_series) as resp_series:
                data_series = await resp_series.json()

        films = data_movie.get("titles", []) + data_series.get("titles", [])

        if not films:
            await message.answer("Не вдалося завантажити фільми")
            return

        await state.update_data(items=films, page=1)
        await send_films_page(message, films, 1)

    except Exception as e:
        logging.error(f"Помилка при завантаженні популярних фільмів: {str(e)}", exc_info=True)
        await message.answer("Сталася помилка при завантаженні фільмів")

# /search
@dp.message(Command("search"))
@async_log_function_call
async def search_films(message: types.Message):
    await message.answer("Оберіть літеру за якою будуть шукатися фільми.\n"
    "Або введіть назву фільму який ви шукаєте:", reply_markup=get_az_keyboard())

# /search_by_genre
@dp.message(Command("search_by_genre"))
@async_log_function_call
async def search_by_genre(message: types.Message):
    await message.answer("Оберіть жанр або введіть вручну:", reply_markup=genre_keyboard())

# Вибір літери
@dp.callback_query(lambda c: c.data.startswith("letter_"))
@async_log_function_call
async def process_letter(callback: types.CallbackQuery, state: FSMContext):
    letter = callback.data.split("_")[1]

    try:
        params = {
            "query": letter
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(SEARCH_API_URL, params=params) as resp:
                data = await resp.json()
                films = data.get("titles", [])

        if not films:
            await callback.message.answer(f"Не знайдено фільмів на літеру {letter}")
            return

        await state.update_data(items=films, page=1)
        await send_films_page(callback.message, films, 1)

    except Exception as e:
        logging.error(f"Помилка при пошуку за літерою {letter}: {str(e)}", exc_info=True)
        await callback.message.answer("Сталася помилка при пошуку")

    await callback.answer()

# Ручне введення назви
@dp.callback_query(lambda c: c.data == "manual_input")
@async_log_function_call
async def manual_input(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введіть назву фільму або серіалу:")
    await state.set_state(FilmStates.waiting_for_query)
    await callback.answer()

@dp.message(FilmStates.waiting_for_query)
@async_log_function_call
async def process_query(message: types.Message, state: FSMContext):
    query = message.text.strip()

    try:
        params = {
            "query": query
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(SEARCH_API_URL, params=params) as resp:
                data = await resp.json()
                films = data.get("titles", [])

        if not films:
            await message.answer(f"Не знайдено фільмів за запитом '{query}'")
            return

        await state.update_data(items=films, page=1)
        await send_films_page(message, films, 1)

    except Exception as e:
        logging.error(f"Помилка при пошуку за назвою '{query}': {str(e)}", exc_info=True)
        await message.answer("Сталася помилка при пошуку")

    await state.clear()

# Вибір жанру з клавіатури
@dp.callback_query(lambda c: c.data.startswith("genre_"))
@async_log_function_call
async def process_genre(callback: types.CallbackQuery, state: FSMContext):
    genre = callback.data.split("_", 1)[1]

    params = {
        "types": "MOVIE",
        "types": "TV_SERIES",
        "genres": genre,
        "sortBy": "SORT_BY_POPULARITY",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, params=params) as resp:
                data = await resp.json()
                films = data.get("titles", [])

        if not films:
            await callback.message.answer(f"Не знайдено фільмів жанру: {genre}")
            return

        await state.update_data(items=films, page=1)
        await send_films_page(callback.message, films, 1)

    except Exception as e:
        logging.error(f"Помилка при пошуку за жанром {genre}: {str(e)}", exc_info=True)
        await callback.message.answer("Сталася помилка при пошуку за жанром.")

    await callback.answer()

# Ручний ввід жанру
@dp.callback_query(lambda c: c.data == "manual_genre_input")
@async_log_function_call
async def manual_genre_input(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введіть жанр вручну (наприклад, Comedy):")
    await state.set_state(FilmStates.waiting_for_genre)
    await callback.answer()

@dp.message(FilmStates.waiting_for_genre)
@async_log_function_call
async def process_manual_genre(message: types.Message, state: FSMContext):
    genre = message.text.strip().title()

    params = {
        "types": "MOVIE",
        "types": "TV_SERIES",
        "genres": genre,
        "sortBy": "SORT_BY_POPULARITY",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, params=params) as resp:
                data = await resp.json()
                films = data.get("titles", [])

        if not films:
            await message.answer(f"Не знайдено фільмів жанру: {genre}")
            return

        await state.update_data(items=films, page=1)
        await send_films_page(message, films, 1)

    except Exception as e:
        logging.error(f"Помилка при ручному пошуку жанру {genre}: {str(e)}", exc_info=True)
        await message.answer("Сталася помилка при пошуку за жанром.")

    await state.clear()

# Сторінки популярних / пошуку
@async_log_function_call
async def send_films_page(chat, films, page):
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_films = films[start:end]

    if not page_films:
        await chat.answer("Більше немає фільмів(обмеження API або фільми за параметром закінчилися).")
        await chat.answer("Використовуйте /search або /search_by_genre для пошуку фільмів.")
        return

    keyboard = build_films_keyboard(page_films, page)
    await chat.answer(f"Сторінка {page}", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("page_"))
@async_log_function_call
async def process_page(callback: types.CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[1])
    data = await state.get_data()
    films = data.get("items", [])
    await send_films_page(callback.message, films, page)
    await callback.answer()

# Деталі фільму
@dp.callback_query(lambda c: c.data.startswith("film_"))
@async_log_function_call
async def show_film_details(callback: CallbackQuery):
    film_id = callback.data.split("_")[1]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/{film_id}") as resp:
                film = await resp.json()

            async with session.get(f"{API_URL}/{film_id}/credits") as resp:
                credits = await resp.json()

        caption = format_film_details(film, credits)
        photo = film.get("primaryImage", {}).get("url")
        

        user = callback.from_user
        favorites = load_favorites(user)
        is_fav = any(f['id'] == film_id for f in favorites)
        if is_fav:
            fav_button_text = "❌ Вилучити з обраного"
        else:
            fav_button_text = "⭐️ Додати в обране"
        fav_callback = f"toggle_fav_{film_id}"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=fav_button_text, callback_data=fav_callback)],
            ]
        )

        if photo:
            await callback.message.answer_photo(photo, caption=caption, parse_mode="HTML", reply_markup=keyboard)
        else:
            await callback.message.answer(caption, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        logging.error(f"Помилка при завантаженні деталей фільму {film_id}: {str(e)}", exc_info=True)
        await callback.message.answer("Не вдалося завантажити інформацію про фільм")

    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("toggle_fav_"))
@async_log_function_call
async def toggle_favorite(callback: CallbackQuery):
    film_id = callback.data.split("_")[2]
    user = callback.from_user

    try:
        # Отримаємо дані фільму (щоб взяти назву для збереження)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/{film_id}") as resp:
                film = await resp.json()

        title = film.get("primaryTitle") or film.get("originalTitle") or "Без назви"
        favorites = load_favorites(user)

        exists = any(f['id'] == film_id for f in favorites)

        if exists:
            favorites = [f for f in favorites if f['id'] != film_id]
            await callback.answer("❌ Вилучено з обраного")
        else:
            favorites.append({"id": film_id, "title": title})
            await callback.answer("⭐️ Додано в обране")

        save_favorites(user, favorites)

        # Оновлюємо кнопку у тому ж повідомленні
        if exists:
            new_text = "⭐️ Додати в обране"
        else:
            new_text = "❌ Вилучити з обраного"

        new_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=new_text, callback_data=f"toggle_fav_{film_id}")]
            ]
        )

        await callback.message.edit_reply_markup(reply_markup=new_keyboard)

    except Exception as e:
        logging.error(f"Помилка при toggling обраного для {film_id}: {e}", exc_info=True)
        await callback.answer("Сталася помилка")

# Тогл додавання/видалення з обраного
@dp.callback_query(lambda c: c.data.startswith("toggle_fav_"))
@async_log_function_call
async def toggle_favorite(callback: types.CallbackQuery):
    film_id = callback.data.split("_")[2]
    user = callback.from_user

    try:
        # Отримаємо дані фільму (щоб взяти назву для збереження)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/{film_id}") as resp:
                film = await resp.json()

        title = film.get("primaryTitle") or film.get("originalTitle") or "Без назви"
        favorites = load_favorites(user)

        # Перевірка чи фільм вже в обраному
        exists = any(f['id'] == film_id for f in favorites)

        if exists:
            favorites = [f for f in favorites if f['id'] != film_id]
            await callback.answer("Вилучено з обраного")
        else:
            favorites.append({"id": film_id, "title": title})
            await callback.answer("Додано в обране")

        save_favorites(user, favorites)

    except Exception as e:
        logging.error(f"Помилка при toggling обраного для {film_id}: {e}", exc_info=True)
        await callback.answer("Сталася помилка")

# /favorites - показ улюблених
@dp.message(Command("favorites"))
@async_log_function_call
async def show_favorites(message: types.Message):
    user = message.from_user
    favorites = load_favorites(user)

    if not favorites:
        await message.answer("У вас поки що немає обраних фільмів.")
        return

    page = 1
    keyboard = build_favorites_keyboard(favorites, page, user.id)
    await message.answer(f"Обрані фільми — сторінка {page}:", reply_markup=keyboard)

# Навігація сторінок у /favorites
@dp.callback_query(lambda c: c.data.startswith("favpage_"))
@async_log_function_call
async def favorite_page(callback: types.CallbackQuery):
    try:
        page = int(callback.data.split("_")[1])
        user = callback.from_user
        favorites = load_favorites(user)

        if not favorites:
            await callback.message.answer("У вас поки що немає обраних фільмів.")
            await callback.answer()
            return

        keyboard = build_favorites_keyboard(favorites, page, user.id)
        await callback.message.edit_text(f"Обрані фільми — сторінка {page}:", reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logging.error(f"Помилка при навігації у обраному: {e}", exc_info=True)
        await callback.answer("Сталася помилка")

# Очищення обраного
@dp.callback_query(lambda c: c.data.startswith("clear_favorites_"))
@async_log_function_call
async def clear_favorites(callback: types.CallbackQuery):
    user_id_str = callback.data.split("_")[2]
    user = callback.from_user

    if str(user.id) != user_id_str:
        await callback.answer("Ви не можете очистити чуже обране", show_alert=True)
        return

    path = get_favorites_path(user)
    if path.exists():
        path.unlink()

    await callback.message.edit_text("Обране очищено.")
    await callback.answer()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))