from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_films_keyboard(films: list[dict], page: int) -> InlineKeyboardMarkup:
    buttons = []
    for film in films:
        title = (
            film.get("primaryTitle")
            or (film.get("titleText", {}).get("text") if isinstance(film.get("titleText"), dict) else None)
            or film.get("originalTitle")
            or "Без назви"
        )[:30]

        fid = film.get("id") or film.get("tconst")
        if fid:
            buttons.append([InlineKeyboardButton(text=title, callback_data=f"film_{fid}")])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Попередня", callback_data="page_" + str(page - 1)))

    nav.append(InlineKeyboardButton(text="➡️ Наступна", callback_data="page_" + str(page + 1)))

    return InlineKeyboardMarkup(inline_keyboard=buttons + [nav])

def genre_keyboard() -> InlineKeyboardMarkup:
    genres = [
        "Action", "Adventure", "Animation", "Comedy", "Crime",
        "Documentary", "Drama", "Fantasy", "Historical", "Horror",
        "Musical", "Mystery", "Romance", "Sci-Fi", "Thriller",
        "War", "Western"
    ]

    buttons = []
    row = []
    for genre in genres:
        row.append(InlineKeyboardButton(text=genre, callback_data=f"genre_{genre}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="Ввести вручну", callback_data="manual_genre_input")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_favorites_keyboard(favorites: list[dict], page: int, user_id: int) -> InlineKeyboardMarkup:
    buttons = []
    per_page = 5
    start = (page - 1) * per_page
    end = start + per_page
    page_favs = favorites[start:end]

    for fav in page_favs:
        title = fav.get("title", "Без назви")[:30]
        fid = fav.get("id")
        if fid:
            buttons.append([InlineKeyboardButton(text=title, callback_data=f"film_{fid}")])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Попередня", callback_data=f"favpage_{page - 1}"))

    if end < len(favorites):
        nav.append(InlineKeyboardButton(text="➡️ Наступна", callback_data=f"favpage_{page + 1}"))

    clear_button = [InlineKeyboardButton(text="🗑 Очистити обране", callback_data=f"clear_favorites_{user_id}")]

    return InlineKeyboardMarkup(inline_keyboard=buttons + ([nav] if nav else []) + [clear_button])
