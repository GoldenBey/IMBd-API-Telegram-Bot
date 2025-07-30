import os
import json

FOLDER = "UserFavorites"
os.makedirs(FOLDER, exist_ok=True)

def get_user_filename(user: dict) -> str:
    username = user.get("username")
    if username:
        return os.path.join(FOLDER, f"@{username}.json")
    else:
        return os.path.join(FOLDER, f"id_{user['id']}.json")

def load_favorites(user: dict) -> set:
    filepath = get_user_filename(user)
    if not os.path.exists(filepath):
        return set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_favorites(user: dict, favorites: set):
    filepath = get_user_filename(user)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(list(favorites), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Error saving favorites: {e}")

def clear_favorites(user: dict):
    filepath = get_user_filename(user)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"❌ Error clearing favorites: {e}")
