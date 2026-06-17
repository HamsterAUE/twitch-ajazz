from time import sleep
import random
import requests
import pygetwindow as gw
import re

from src.core.action import Action
from src.core.logger import Logger

class SendRandomEmote(Action):
    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)
        self.current_streamer = None
        self.cached_emotes = []
        self.KEYWORDS = []
        self.TAGS = []
        self.EXCLUDE = []



    def update_cache(self, streamer):
        self.cached_emotes = []
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
            proxies = {
                'http': 'socks5h://127.0.0.1:40000',
                'https': 'socks5h://127.0.0.1:40000'
            }
            response = requests.post(url, json=payload, proxies=proxies, timeout=(3.05, 7))

            if response.status_code == 200:
                data = response.json()

                # 1. Забираем массив результатов поиска пользователей
                user_results = data.get("data", {}).get("users", {})
                if not user_results:
                    Logger.warning(f"[SendRandomEmote]No user with nickname {streamer} was found on 7tv.")
                    self.cached_emotes = []
                    return

                # Берем первого найденного пользователя
                user_data = user_results[0]
                # 2. Ищем активный emote_set_id конкретно для Твича в массиве connections
                connections = user_data.get("connections", [])
                connection = next((c for c in connections if c.get("platform") == "TWITCH"), None)

                if not connection:
                    Logger.warning(f"[SendRandomEmote]У пользователя {streamer} нет подключенного Twitch аккаунта на 7TV.")
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
                    Logger.info(f"[SendRandomEmote]Success caching {len(self.cached_emotes)} emotes for {streamer}")
                else:
                    Logger.warning(f"[SendRandomEmote]Couldn't find emotes from EmoteSet with ID {active_set_id}")
                    self.cached_emotes = []

        except Exception as e:
            Logger.error(f"[SendRandomEmote]Cant get 7TV emotes by Exception: {e}")



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
            Logger.error("[SendRandomEmote]Failed to get Twitch streamer info. Exception: {}".format(e))
        return None



    def filter_emotes(self):
        if not self.cached_emotes:
            return []

        suitable_emotes = []
        #TAGS --> Список тегов 7TV, которые точно указывают на приветствие
        #KEYWORDS --> Регулярное выражение для поиска корней приветствия в имени смайлика
        #EXCLUDE --> Конкретное название эмоуа требующего исключения

        for emote in self.cached_emotes:
            name = emote["name"]
            tags = emote["tags"]
            name_lower = name.lower()

            emote_fits = False
            # Способ 1: Проверка по тегам 7TV (Самый точный)
            if set(tags).intersection(self.TAGS):
                emote_fits = True

            # Способ 2: Проверка на точное совпадение имени целиком
            if name_lower in self.KEYWORDS:
                emote_fits = True


            if emote_fits and not any(smile in name for smile in self.EXCLUDE):
                suitable_emotes.append(name)
        random.shuffle(suitable_emotes)
        return suitable_emotes



    def on_key_up(self, payload):
        detected_streamer = self.get_current_twitch_streamer()
        if not detected_streamer:
            Logger.warning("[SendRandomEmote] No Twitch tab detected.")
            return
        if detected_streamer != self.current_streamer:
            # Вызываем метод обновления кэша
            self.update_cache(detected_streamer)

        valid_greeting_emotes = self.filter_emotes()

        if valid_greeting_emotes:

            import pyperclip
            import pyautogui
            import keyboard

            # Выбираем от 1 до 3 случайных приветственных смайликов
            x = random.randint(1, 4)
            count = min(x, len(valid_greeting_emotes))
            chosen_smiles = random.sample(valid_greeting_emotes, count)
            text_to_insert = " " + " ".join(chosen_smiles)

            try:
                # 1. Запоминаем текущий буфер
                old_clipboard = pyperclip.paste()

                # 2. Копируем наши смайлы
                pyperclip.copy(text_to_insert)
                Logger.info(f"[SendRandomEmote] Копирование")
                sleep(0.1)
                keyboard.send("ctrl+v")
                Logger.info(f"[SendRandomEmote] Вставка {pyperclip.paste()}")
                sleep(0.4)

                # 5. Возвращаем старый текст
                pyperclip.copy(old_clipboard)

                Logger.info(f"[SendRandomEmote] Успешно дозаписаны смайлики для {detected_streamer}: {text_to_insert}")
            except Exception as e:
                Logger.error(f"[SendRandomEmote] Ошибка при эмуляции клавиатуры/буфера: {e}")
        else:
            Logger.warning(f"[SendRandomEmote] На канале {detected_streamer} не найдено подходящих смайликов.")


class HiiSmiles(Action, SendRandomEmote):
    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)

        self.current_streamer = None
        self.cached_emotes = []

    def update_cache(self, streamer):
        self.cached_emotes = []
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
            proxies = {
                'http': 'socks5h://127.0.0.1:40000',
                'https': 'socks5h://127.0.0.1:40000'
            }
            response = requests.post(url, json=payload,proxies=proxies, timeout=(3.05, 7))

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

        EXCLUDE_SMILES = ["JUDGE", "fm", "raid"]


        for emote in self.cached_emotes:
            name = emote["name"]
            tags = emote["tags"]
            name_lower = name.lower()

            is_greeting = False
            # Способ 1: Проверка по тегам 7TV (Самый точный)
            if set(tags).intersection(HI_TAGS):
                is_greeting = True

            # Способ 2: Проверка на точное совпадение имени целиком

            if name_lower in keywords:
                is_greeting = True

            # Проверка на затяжные одиночные приветствия (yoоооо / hiiiii)
            elif re.match(r'^yo+$', name_lower) or re.match(r'^hi+$', name_lower):
                is_greeting = True

            else:
                # Способ 3: Разделение CamelCase и умная проверка начала/конца
                spaced_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
                words = spaced_name.lower().split()
                if words:
                    first_word = words[0]
                    last_word = words[-1]


                    if re.match(r'^hi+', first_word) or re.match(r'^yo+', first_word):
                        if len(first_word) <= 4 and "you" not in first_word:
                            is_greeting = True

                    if re.match(r'.*hi+$', last_word) or re.match(r'.*yo+$', last_word):
                        if len(last_word) <= 4 and "you" not in last_word:
                            is_greeting = True

            # Способ 4: Финальный предохранитель (Жёсткий отбор для смайликов БЕЗ тегов)
            if not is_greeting and not tags:
                if (name_lower.startswith("hi") or name_lower.startswith("yo") or name_lower.endswith("yo")
                or name_lower.endswith("hi")):
                    is_greeting = True

            if is_greeting and not any(smile in name for smile in EXCLUDE_SMILES):
                greeting_emotes.append(name)
        random.shuffle(greeting_emotes)
        return greeting_emotes

    def on_key_up(self, payload):
        detected_streamer = self.get_current_twitch_streamer()
        if not detected_streamer:
            Logger.warning("[HiiSmiles] No Twitch tab detected.")
            return
        if detected_streamer != self.current_streamer:
            # Вызываем метод обновления кэша
            self.update_cache(detected_streamer)

        valid_greeting_emotes = self.filter_hi_emotes()

        if valid_greeting_emotes:

            import pyperclip
            import pyautogui
            import keyboard

            # Выбираем от 1 до 3 случайных приветственных смайликов
            x = random.randint(1, 4)
            count = min(x, len(valid_greeting_emotes))
            chosen_smiles = random.sample(valid_greeting_emotes, count)
            text_to_insert = " " + " ".join(chosen_smiles)

            try:
                # 1. Запоминаем текущий буфер
                old_clipboard = pyperclip.paste()

                # 2. Копируем наши смайлы
                pyperclip.copy(text_to_insert)
                Logger.info(f"[HiiSmiles] Копирование")
                sleep(0.1)
                keyboard.send("ctrl+v")
                Logger.info(f"[HiiSmiles] Вставка {pyperclip.paste()}")
                sleep(0.4)

                # 5. Возвращаем старый текст
                pyperclip.copy(old_clipboard)

                Logger.info(f"[HiiSmiles] Успешно дозаписаны смайлики для {detected_streamer}: {text_to_insert}")
            except Exception as e:
                Logger.error(f"[HiiSmiles] Ошибка при эмуляции клавиатуры/буфера: {e}")
        else:
            Logger.warning(f"[HiiSmiles] На канале {detected_streamer} не найдено подходящих приветственных смайликов.")

class SpeedEmotes(Action, SendRandomEmote):
    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)

        self.current_streamer = None
        self.cached_emotes = []
        self.KEYWORDS = []
        self.TAGS = []
        self.EXCLUDE = []