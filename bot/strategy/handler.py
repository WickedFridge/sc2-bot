from typing import List, Optional
from bot.macro.macro import BASE_SIZE
from bot.strategy.strategy_types import Priority, Situation, Strategy
from bot.superbot import Superbot
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from ..utils.unit_tags import tower_types


class StrategyHandler:
    bot: Superbot
    situation: Situation
    strategy: Strategy
    priorities: List[Priority]
    BASE_SIZE: int = 20

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.situation = Situation.STABLE
        self.strategy = Strategy.MACRO_SAFE
        self.priorities = [
            Priority.ECONOMY,
            Priority.BUILD_DEFENSE,
            Priority.TECH,
            Priority.BUILD_ARMY
        ]

    async def update_situation(self):
        self.situation = self.assess_situation()

    def assess_situation(self) -> Situation:
        # identify canon rush or bunker rush
        tower_rush_situation: Optional[Situation] = self.detect_tower_rush()
        if (tower_rush_situation):
            return tower_rush_situation            

        return Situation.STABLE
    
    def detect_tower_rush(self) -> Optional[Situation]:
        if self.bot.townhalls.amount >= 3:
            return None
        # we only detect towers in the main and b2 as canon rush
        enemy_towers: Units = self.bot.enemy_structures.filter(
            lambda unit: (
                unit.type_id in tower_types
                and (
                    unit.distance_to(self.bot.expansions.b2.position) <= self.BASE_SIZE
                    or unit.distance_to(self.bot.expansions.main.position) <= self.BASE_SIZE
                )
            )
        )
        if (enemy_towers.amount >= 1):
            match(enemy_towers.random.type_id):
                case UnitTypeId.PYLON:
                    return Situation.CANON_RUSH
                case UnitTypeId.PHOTONCANNON:
                    return Situation.CANON_RUSH
                case UnitTypeId.BUNKER:
                    return Situation.BUNKER_RUSH
                case _:
                    return Situation.UNDER_ATTACK