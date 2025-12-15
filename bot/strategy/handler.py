from typing import List, Optional
from bot.macro.expansion import Expansion
from bot.macro.macro import BASE_SIZE
from bot.strategy.build_order.builds.conservative_expand import ConservativeExpand
from bot.strategy.build_order.builds.two_rax_reapers import TwoRaxReapers
from bot.strategy.strategy_types import Priority, Situation, Strategy
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.matchup import Matchup
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types

class StrategyHandler:
    bot: Superbot
    strategy: Strategy
    priorities: List[Priority]
    situation_history: List[Situation] = []
    BASE_SIZE: int = 20

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.strategy = Strategy.MACRO_SAFE
        self.priorities = [
            Priority.ECONOMY,
            Priority.BUILD_DEFENSE,
            Priority.TECH,
            Priority.BUILD_ARMY
        ]

    async def update_situation(self):
        new_situation: Situation = self.assess_situation()
        if (new_situation == self.bot.scouting.situation):
            return
        print(f'Situation update : {new_situation}')
        print(f'Situation history : {self.situation_history}')
        self.situation_history.append(new_situation)
        await self.bot.client.chat_send(f'Situation update : {new_situation}', False)
        self.bot.scouting.situation = new_situation

    def assess_situation(self) -> Situation:
        # identify canon rush or bunker rush
        tower_rush_situation: Optional[Situation] = self.detect_tower_rush()
        if (tower_rush_situation):
            return tower_rush_situation
        
        early_cheese_situation: Optional[Situation] = self.detect_early_cheese()
        if (early_cheese_situation):
            return early_cheese_situation
        
        fighting_units: Units = self.bot.units.filter(lambda unit: unit.type_id not in worker_types)
        army: Army = Army(fighting_units, self.bot)
        OVER_POWERED_RATIO: float = 2
        if (self.bot.scouting.known_enemy_army.fighting_supply >= OVER_POWERED_RATIO * army.supply + 1):
            return Situation.UNDER_ATTACK
        return Situation.STABLE
    
    def detect_early_cheese(self):
        if (self.bot.townhalls.amount >= 3):
            return None
        
        main: Point2 = self.bot.expansions.main.position
        b2: Point2 = self.bot.expansions.b2.position
        SAFETY_DISTANCE: int = 25

        menacing_enemy_units: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.distance_to(main) < SAFETY_DISTANCE
                or unit.distance_to(b2) < SAFETY_DISTANCE
            )
        )

        proxy_buildings: Units = self.bot.enemy_structures.filter(
            lambda building: building.distance_to(self.bot.expansions.main.position) < building.distance_to(self.bot.expansions.enemy_main.position)
        )
        if (proxy_buildings.amount >= 1):
            return Situation.PROXY_BUILDINGS
        
        if (menacing_enemy_units.amount == 0):
            return None

        # detect ling drone rush
        zerglings: Units = menacing_enemy_units(UnitTypeId.ZERGLING)
        drones: Units = menacing_enemy_units(UnitTypeId.DRONE)
        if (
            zerglings.amount >= 2
            and drones.amount >= 2
        ):
            return Situation.CHEESE_LING_DRONE
    
    async def cheese_response(self):
        if (self.bot.scouting.situation == Situation.CHEESE_LING_DRONE):
            # cancel B2 and switch towards Conservative Expand
            expand_in_construction: Units = self.bot.townhalls.not_ready
            if (expand_in_construction):
                expand_in_construction.first(AbilityId.CANCEL_BUILDINPROGRESS)
            
            self.bot.build_order.build = ConservativeExpand(self.bot)
            return
        if (self.bot.scouting.situation == Situation.PROXY_BUILDINGS):
            self.bot.build_order.build = ConservativeExpand(self.bot)
    
    def detect_tower_rush(self) -> Optional[Situation]:
        if (self.bot.townhalls.amount >= 3):
            return None
        # we only detect towers in the main and b2 as canon rush
        enemy_towers: Units = self.bot.enemy_structures.filter(
            lambda unit: (
                (unit.type_id in tower_types or unit.type_id == UnitTypeId.PYLON)
                and (
                    unit.distance_to(self.bot.expansions.b2.position) <= self.BASE_SIZE
                    or unit.distance_to(self.bot.expansions.main.position) <= self.BASE_SIZE
                )
            )
        )
        if (enemy_towers.amount >= 1):
            match(enemy_towers.first.type_id):
                case UnitTypeId.PYLON:
                    return Situation.CANON_RUSH
                case UnitTypeId.PHOTONCANNON:
                    return Situation.CANON_RUSH
                case UnitTypeId.BUNKER:
                    return Situation.BUNKER_RUSH
                case _:
                    return Situation.UNDER_ATTACK