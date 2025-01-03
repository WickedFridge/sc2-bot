from datetime import datetime
import random
import sc2
from bot.bot import WickedBot
from sc2.data import Race
from sc2.main import run_game
from sc2.player import Bot, Computer, Human

def main():
    all_maps = [
        "AbyssalReefAIE",
        # "Gresvan512AIE",
        # "Goldenaura512AIE",
        # "HardLead512AIE",
        # "Oceanborn512AIE",
        # "SiteDelta512AIE",
    ]
    map = random.choice(all_maps)
    run_game(
        sc2.maps.get(map),  # pyright: ignore
        [Human(Race.Protoss), Bot(Race.Terran, WickedBot())],
        save_replay_as="replays/"f"{datetime.utcnow().strftime('%Y%m%d_%H%M')}.SC2Replay",
        realtime=True,
    )

if __name__ == "__main__":
    main()
