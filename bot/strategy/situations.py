from typing import List
from bot.strategy.strategy_types import Situation

precarious_situations: List[Situation] = [
    Situation.PROXY_BUILDINGS,
    Situation.UNDER_ATTACK,
    Situation.CHEESE_LING_DRONE,
    Situation.CHEESE_ROACH_RUSH,
    Situation.CHEESE_UNKNOWN,
]