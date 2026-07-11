from pathlib import Path
from typing import List
import jsonpickle
import os
from bot.superbot import Superbot
DATA_FOLDER = "data"

class Analytics:
    bot: Superbot
    file_name: str = f"{DATA_FOLDER}/results.json"
    data: List[str] = []
    
    def __init__(self, bot: Superbot) -> None:
        self.bot = bot

    def read_data(self):
        with open(self.file_name, "r") as handle:
            text = handle.read()
            # Compatibility with older versions to prevent crashes
            self.data: List[str] = jsonpickle.decode(text)
    
    def write(self, data: str):
        my_file = Path(self.file_name)

        if my_file.is_file():
            try:
                self.read_data()
            except Exception as e:
                # Don't write if we can't read the current data
                print(f"Data read failed on save: {e}")
                return
        elif not os.path.exists(DATA_FOLDER):
            os.makedirs(DATA_FOLDER)

        self.data.append(data)

        frozen = jsonpickle.encode(self.data)
        try:
            with open(self.file_name, "w") as handle:
                handle.write(frozen)
        except Exception as e:
            print(f"Data write failed: {e}")