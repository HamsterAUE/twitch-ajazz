import json
from typing import Optional

import time
from PIL import Image, ImageDraw
import io
import base64
import requests
import pygetwindow as gw
import re

from src.core.action import Action
from src.core.logger import Logger

class HiiSmiles(Action):
    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)

        self.current_streamer = None
        self.cached_emotes = []

    def update_cache(self, streamer):
        url = "https://7tv.io/v3/gql"
        query = """
            query Users($query: String!, $limit: Int) {
              users(query: $query, limit: $limit) {
                emote_sets {
                  id
                  emotes {
                    name
                    data {
                      tags
                    }
                  }
                }
                connections {
                  emote_set_id
                  platform
                }
              }
            }
        """
        try:
            Logger.info(f"Loading 7TV emotes from: {streamer}")
            payload = {
                "query": query,
                "variables": {"query": streamer, "limit": 1}
            }
            response = requests.post(url, json=payload, timeout=3)

            if response.status_code == 200:
                data = response.json()

                # 1. Забираем массив результатов поиска пользователей
                user_results = data.get("data", {}).get("users", {})
                if not user_results:
                    Logger.warning(f"No user with nickname {streamer} was found on 7tv.")
                    self.cached_emotes = []
                    return

                # Берем первого найденного пользователя
                user_data = user_results[0]
                # 2. Ищем активный emote_set_id конкретно для Твича в массиве connections
                connections = user_data.get("connections", [])
                connection = next((c for c in connections if c.get("platform") == "TWITCH"), None)

                if not connection:
                    Logger.warning(f"У пользователя {streamer} нет подключенного Twitch аккаунта на 7TV.")
                    connection = connections[0]


                active_set_id = connection.get("emote_set_id")

                # 3. Теперь ищем сам emote_set с этим ID внутри массива emote_sets
                emote_sets = user_data.get("emote_sets", [])
                active_set = next((s for s in emote_sets if s.get("id") == active_set_id), None)

                if active_set:
                    emotes_raw = active_set.get("emotes", [])
                    for emote in emotes_raw:
                        name = emote.get("name")
                        tags = emote.get("data", {}).get("tags", [])
                        tags = [t.lower() for t in tags if t]
                        self.cached_emotes.append({
                            "name": name,
                            "tags": tags
                        })
                        self.current_streamer = streamer
                    Logger.info(f"Success caching {len(self.cached_emotes)} emotes for {streamer}")
                else:
                    Logger.warning(f"Couldn't find emotes from EmoteSet with ID {active_set_id}")
                    self.cached_emotes = []

        except Exception as e:
            Logger.error(f"Cant get 7TV emotes by Exception: {e}")
            self.cached_emotes = []


    def get_current_twitch_streamer(self):
        try:
            # Получаем окно, которое сейчас открыто перед пользователем
            active_window = gw.getActiveWindow()
            if active_window and "- Twitch" in active_window.title:
                # Название обычно идет в формате "НИКНЕЙМ - Twitch"
                # С помощью регулярного выражения забираем всё, что идет до дефиса
                match = re.search(r"^(.*?)\s*-\s*Twitch", active_window.title)
                if match:
                    # Переводим в нижний регистр для API и убираем лишние пробелы
                    return match.group(1).strip().lower()
        except Exception as e:
            Logger.error("[HiiSmiles] Failed to get Twitch streamer info. Exception: {}".format(e))
        return None


# Фильтрует кэш смайликов и возвращает только приветственные
    def filter_hi_emotes(self):
        if not self.cached_emotes:
            return []

        greeting_emotes = []

        # Список тегов 7TV, которые точно указывают на приветствие
        HI_TAGS = {"hello", "hi", "hii", "wave", "greeting", "welcome", "qq", "yo", "sup"}

        # Регулярное выражение для поиска корней приветствия в имени смайлика
        keywords = ["qq", "ky", "hi", "hii", "priv", "hello", "yo", "agahi", "tahi", "qqq"]

        for emote in self.cached_emotes:
            name = emote["name"]
            tags = emote["tags"]

            # Способ 1: Проверка по тегам 7TV (Самый точный)
            if set(tags).intersection(HI_TAGS):
                greeting_emotes.append(name)
                continue  # Смайлик прошел проверку, идем к следующему

            # Способ 2: Проверка на точное совпадение имени целиком
            name_lower = name.lower()
            if name_lower in keywords:
                greeting_emotes.append(name)
                continue

            # Проверка на затяжные одиночные приветствия (yoоооо / hiiiii)
            if re.match(r'^yo+$', name_lower) or re.match(r'^hi+$', name_lower):
                greeting_emotes.append(name)
                continue

            # Способ 3: Разделение CamelCase и умная проверка начала/конца
            spaced_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
            words = spaced_name.lower().split()
            if words:
                first_word = words[0]
                last_word = words[-1]
                passed_camel_check = False

                if re.match(r'^hi+', first_word) or re.match(r'^yo+', first_word):
                    if len(first_word) <= 4:
                        passed_camel_check = True

                if re.match(r'.*hi+$', last_word) or re.match(r'.*yo+$', last_word):
                    if len(last_word) <= 4:
                        passed_camel_check = True

                if passed_camel_check:
                    greeting_emotes.append(name)
                    continue

            # Способ 4: Финальный предохранитель (Жёсткий отбор для смайликов БЕЗ тегов)
            if not tags:
                starts_with_hi_or_yo = name_lower.startswith("hi") or name_lower.startswith("yo")
                ends_with_hi_or_yo = name_lower.endswith("yo") or name_lower.endswith("hi")

                if starts_with_hi_or_yo or ends_with_hi_or_yo:
                    greeting_emotes.append(name)
                    continue

        return greeting_emotes

    def on_key_up(self, payload):
        detected_streamer = self.get_current_twitch_streamer()
        if not detected_streamer:
            Logger.warning("[HiiSmiles] No Twitch tab detected.")
            return
        if detected_streamer != self.current_streamer:
            # Вызываем метод обновления кэша
            self.update_cache(self, detected_streamer)

        valid_greeting_emotes = self.filter_hi_emotes()

        if valid_greeting_emotes:
            import random
            import pyperclip
            import pyautogui

            # Выбираем от 1 до 3 случайных приветственных смайликов
            count = min(3, len(valid_greeting_emotes))
            chosen_smiles = random.sample(valid_greeting_emotes, count)
            text_to_insert = " " + " ".join(chosen_smiles)

            try:
                # Сохраняем текущее содержимое буфера обмена пользователя
                old_clipboard = pyperclip.paste()

                pyperclip.copy(text_to_insert)

                pyautogui.hotkey('ctrl', 'v')

                # Небольшая пауза, чтобы Windows успел выполнить операцию вставки
                time.sleep(0.05)

                # Возвращаем пользователю его старый текст в буфер обмена
                pyperclip.copy(old_clipboard)

                Logger.info(f"[HiiSmiles] Успешно дозаписаны смайлики для {detected_streamer}: {text_to_insert}")
            except Exception as e:
                Logger.error(f"[HiiSmiles] Ошибка при эмуляции клавиатуры/буфера: {e}")
        else:
            Logger.warning(f"[HiiSmiles] На канале {detected_streamer} не найдено подходящих приветственных смайликов.")
