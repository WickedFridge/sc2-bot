from collections.abc import Callable
import math
from typing import Any, List, Optional, Union
from bot.combat.micro_units.cyclone import MicroCyclone
from bot.combat.micro_units.ghost import MicroGhost
from bot.combat.micro_units.hellion import MicroHellion
from bot.combat.micro_units.marauder import MicroMarauder
from bot.combat.micro_units.marine import MicroMarine
from bot.combat.micro_units.medivac import MicroMedivac
from bot.combat.micro_units.micro_unit import MicroUnit
from bot.combat.micro_units.raven import MicroRaven
from bot.combat.micro_units.reaper import MicroReaper
from bot.combat.micro_units.siege_tank import MicroSiegeTank
from bot.combat.micro_units.thor import MicroThor
from bot.combat.micro_units.viking import MicroViking
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.point2_functions.utils import center
from bot.utils.unit_supply import get_unit_supply
from sc2.cache import CachedClass, custom_cache_once_per_frame
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, dont_attack, hq_types, menacing, bio_stimmable, building_priorities, creep

from s2clientprotocol import raw_pb2 as raw_pb
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import ui_pb2 as ui_pb

WEAPON_READY_THRESHOLD: float = 6.0

class Micro(CachedClass):
    bot: Superbot
    marine: MicroMarine
    marauder: MicroMarauder
    reaper: MicroReaper
    ghost: MicroGhost
    hellion: MicroHellion
    cyclone: MicroCyclone
    siege_tank: MicroSiegeTank
    thor: MicroThor
    medivac: MicroMedivac
    viking: MicroViking
    raven: MicroRaven
    handlers: dict[UnitTypeId, MicroUnit]

    def __init__(self, bot):
        super().__init__(bot)
        self.marine = MicroMarine(self.bot)
        self.marauder = MicroMarauder(self.bot)
        self.reaper = MicroReaper(self.bot)
        self.ghost = MicroGhost(self.bot)
        self.hellion = MicroHellion(self.bot)
        self.cyclone = MicroCyclone(self.bot)
        self.siege_tank = MicroSiegeTank(self.bot)
        self.thor = MicroThor(self.bot)
        self.medivac = MicroMedivac(self.bot)
        self.viking = MicroViking(self.bot)
        self.raven = MicroRaven(self.bot)

        self.handlers = {
            UnitTypeId.MARINE: self.marine,
            UnitTypeId.MARAUDER: self.marauder,
            UnitTypeId.REAPER: self.reaper,
            UnitTypeId.GHOST: self.ghost,
            UnitTypeId.HELLION: self.hellion,
            UnitTypeId.CYCLONE: self.cyclone,
            UnitTypeId.SIEGETANK: self.siege_tank,
            UnitTypeId.SIEGETANKSIEGED: self.siege_tank,
            UnitTypeId.THOR: self.thor,
            UnitTypeId.THORAP: self.thor,
            UnitTypeId.MEDIVAC: self.medivac,
            UnitTypeId.VIKINGFIGHTER: self.viking,
            UnitTypeId.RAVEN: self.raven
        }

    def get_nearest_base_target(self, unit: Unit) -> Point2:
        if (self.bot.expansions.enemy_bases.amount >= 1):
            return self.bot.expansions.enemy_bases.closest_to(unit).position
        elif (self.bot.expansions.enemy_main.is_unknown):
            return self.bot.expansions.enemy_main.position
        else:
            return self.bot.expansions.sorted(lambda expansion: expansion.distance_from_main, True).sorted_by_oldest_scout().first.position

    def worker_attack(bot: Superbot, worker: Unit, target: Unit):
        if (worker.weapon_cooldown < 4):
            print("worker attack !")
            worker.attack(target)
        else:
            if (bot.mineral_field.amount == 0):
                return
            closest_mineral_field: Unit = bot.mineral_field.closest_to(worker)
            print("worker back !")
            worker.gather(closest_mineral_field)