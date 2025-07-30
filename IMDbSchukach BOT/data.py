import aiohttp
import logging

API_BASE_URL = "https://api.imdbapi.dev"

async def search_imdb_titles(params: dict) -> dict:
    """
    Виконує пошук або запит списку фільмів з IMDb.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/search/titles", params=params) as resp:
                if resp.status != 200:
                    logging.error(f"API returned status {resp.status}")
                    return {"results": []}
                
                data = await resp.json()
                
                if "titles" in data:
                    return {"results": data["titles"]}
                elif "results" in data:
                    return {"results": data["results"]}
                else:
                    logging.error(f"Unexpected API response format: {data}")
                    return {"results": []}
                
    except aiohttp.ClientError as e:
        logging.error(f"Network error: {e}")
        return {"results": []}
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {"results": []}

def format_film_details(film, credits):
    # Основна інформація про фільм
    title = film.get('primaryTitle', film.get('originalTitle', 'Назва невідома'))
    year = film.get('startYear', '?')
    rating_data = film.get('rating', {})
    rating = rating_data.get('aggregateRating', '?')
    vote_count = rating_data.get('voteCount', '?')
    plot = film.get('plot', 'Опис відсутній')
    runtime = film.get('runtimeSeconds', 0)
    
    # Конвертація часу з секунд у хвилини
    if runtime:
        runtime = f"{runtime // 60} хв"
    else:
        runtime = "?"
    
    # Жанри
    genres = ', '.join(film.get('genres', [])) or 'Невідомо'
    
    caption = (
        f"🎬 <b>{title}</b>\n"
        f"📅 <b>Рік:</b> {year}\n"
        f"⏳ <b>Тривалість:</b> {runtime}\n"
        f"🏷️ <b>Жанр:</b> {genres}\n"
        f"⭐ <b>Рейтинг IMDb:</b> {rating}/10 (голосів: {vote_count})\n"
        f"📝 <b>Опис:</b> {plot}"
    )
    
    # Обробка акторів (якщо credits доступні)
    if credits and isinstance(credits, dict):
        actors = credits.get('cast', [])
        if actors:
            actor_names = []
            for actor in actors:
                if isinstance(actor, dict) and 'name' in actor:
                    actor_names.append(actor['name'])
                elif isinstance(actor, str):
                    actor_names.append(actor)
            
            if actor_names:
                caption += f"\n\n🎭 <b>Актори:</b> {', '.join(actor_names[:5])}"  # Перші 5 акторів
                if len(actor_names) > 5:
                    caption += f" та інші..."
    
    return caption[:1024]  # Обмеження довжини до 1024 символів для Telegram