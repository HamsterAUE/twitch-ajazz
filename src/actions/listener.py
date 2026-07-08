import json
import os
import subprocess
import base64

from src.core.action import Action
from src.core.logger import Logger

class SelfListener(Action):
    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)
        self.is_listening = False
        current_dir = os.path.dirname(os.path.abspath(__file__))
        tools_folder_path = os.path.abspath(os.path.join(current_dir, "..", "tools"))
        self.tool_path = os.path.join(tools_folder_path, "SoundVolumeView.exe")
        self.tool_path = os.path.normpath(self.tool_path)

        self.devices_json_path = os.path.normpath(os.path.join(tools_folder_path, "devices.json"))

        self.img_on_path = os.path.normpath(os.path.join(current_dir, "..", "..", "static", "img", "talk.png"))
        self.img_off_path = os.path.normpath(os.path.join(current_dir, "..", "..", "static", "img", "netalk.png"))

        self.is_listening = self.get_current_listen_state()
        self.update_img()

    def _get_image_as_base64(self, file_path: str):
        """Читает файл с диска и конвертирует его в формат Data URL Base64"""
        try:
            if not os.path.exists(file_path):
                Logger.error(f"[ListenMic] Файл картинки не найден: {file_path}")
                return ""
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            ext = os.path.splitext(file_path)[1].replace(".", "").lower()
            if ext == "jpg": ext = "jpeg"

            return f"data:image/{ext};base64,{encoded_string}"

        except Exception as e:
            Logger.error(f"[ListenMic] Ошибка кодирования картинки: {e}")
            return ""

    def update_img(self):
        if self.is_listening:
            url = self._get_image_as_base64(self.img_on_path)
            if url:
                self.set_image(url)
        else:
            url = self._get_image_as_base64(self.img_off_path)
            if url:
                self.set_image(url)


    def _get_devices_from_json(self):
        try:
            comand = f"{self.tool_path} /sjson {self.devices_json_path}"
            result = subprocess.run(comand, shell=True, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                attempts = 0
                while (not os.path.exists(self.devices_json_path) or os.path.getsize(self.devices_json_path) == 0) and attempts < 10:
                    import time
                    time.sleep(0.05)
                    attempts += 1

                # Если файл так и не ожил — вызываем ошибку
                if not os.path.exists(self.devices_json_path) or os.path.getsize(self.devices_json_path) == 0:
                    raise Exception("Файл устройств пуст или не был создан ОС")

                with open(self.devices_json_path, "r", encoding='utf-16') as devices_json:
                    devices = json.load(devices_json)
                    return devices
        except Exception as e:
            Logger.error(f"[ListenMic] Ошибка получения списка устройств: {e}")
            return []
        finally:
            if os.path.exists(self.devices_json_path):
                os.remove(self.devices_json_path)


    def get_default_microphone_name(self):
        """Автоматически находит имя микрофона по умолчанию в Windows"""
        try:
            devices = self._get_devices_from_json()
            for device in devices:
                if device.get("Direction") == "Capture" and device.get("Default", ""):
                    mic_name = device.get("Name")
                    Logger.info(f"[ListenMic] Найдено девайс по умолчанию: {mic_name}")

                    return mic_name

        except Exception as e:
            Logger.error(f"[ListenMic] Ошибка при поиске микрофона: {e}")
        return ""

    def get_current_listen_state(self) -> bool:
        """Проверяет в Windows, включено ли прослушивание для дефолтного микрофона прямо сейчас"""
        try:
            devices = self._get_devices_from_json()
            for device in devices:
                if device.get("Direction") == "Capture" and device.get("Default", ""):
                    listen_state = device.get("Listen To This Device", "No")
                    Logger.info(f"[ListenMic] Текущий статус прослушивания в Windows: {listen_state}")

                    return listen_state == "Yes"

        except Exception as e:
            Logger.error(f"[ListenMic] Не удалось получить статус прослушивания: {e}")
        return False


    def on_key_up(self,payload):
        mic_name = self.get_default_microphone_name()
        try:
            if not self.is_listening:
                comand = f'"{self.tool_path}" /SetListenToThisDevice "{mic_name}" 1'
                subprocess.run(comand, shell=True, check=True)

                self.is_listening = True

                Logger.info(f"[ListenMic] Прослушивание микрофона {mic_name} ВКЛЮЧЕНО")
            else:
                comand = f'"{self.tool_path}" /SetListenToThisDevice "{mic_name}" 0'
                subprocess.run(comand, shell=True, check=True)

                self.is_listening = False
                Logger.info(f"[ListenMic] Прослушивание микрофона {mic_name} ВЫКЛЮЧЕНО")
            self.update_img()
        except Exception as e:
            Logger.error(f"[ListenMic] Ошибка выполнения команды: {e}")