from collections.abc import Callable
from typing import Awaitable, Dict, List
from bot.combat.select_orders import SelectOrders
from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.units.banshee import Banshee
from bot.units.cyclone import Cyclone
from bot.units.ghost import Ghost
from bot.units.hellion import Hellion
from bot.units.marauder import Marauder
from bot.units.marine import Marine
from bot.units.medivac import Medivac
from bot.units.raven import Raven
from bot.units.reaper import Reaper
from bot.units.scv import Scv
from bot.units.siegetank import SiegeTank
from bot.units.thor import Thor
from bot.units.train import Train
from bot.units.viking import Viking
from sc2.ids.unit_typeid import UnitTypeId

class TrainerFunction:
    function: Callable[[Resources], Awaitable[Resources]]
    ratio: float

    def __init__(self, function: Callable[[Resources], Awaitable[Resources]], ratio: float = 1):
        self.function = function
        self.ratio = ratio

class Trainer:
    bot: Superbot
    combat: SelectOrders
    scv: Scv
    reaper: Reaper
    marine: Marine
    marauder: Marauder
    medivac: Medivac
    ghost: Ghost
    hellion: Hellion
    cyclone: Cyclone
    siegetank: SiegeTank
    thor: Thor
    viking: Viking
    banshee: Banshee
    raven: Raven
    army_trainers: Dict[UnitTypeId, Train]
    
    def __init__(self, bot: Superbot, combat: SelectOrders) -> None:
        self.bot = bot
        self.combat = combat
        self.scv = Scv(self)
        self.reaper = Reaper(self)
        self.marine = Marine(self)
        self.marauder = Marauder(self)
        self.medivac = Medivac(self)
        self.hellion = Hellion(self)
        self.ghost = Ghost(self)
        self.cyclone = Cyclone(self)
        self.siegetank = SiegeTank(self)
        self.thor = Thor(self)
        self.viking = Viking(self)
        self.banshee = Banshee(self)
        self.raven = Raven(self)
        
        self.army_trainers = {
            UnitTypeId.REAPER: self.reaper,
            UnitTypeId.MARINE: self.marine,
            UnitTypeId.MARAUDER: self.marauder,
            UnitTypeId.MEDIVAC: self.medivac,
            UnitTypeId.GHOST: self.ghost,
            UnitTypeId.HELLION: self.hellion,
            UnitTypeId.CYCLONE: self.cyclone,
            UnitTypeId.SIEGETANK: self.siegetank,
            UnitTypeId.THOR: self.thor,
            UnitTypeId.VIKINGFIGHTER: self.viking,
            UnitTypeId.BANSHEE: self.banshee,
            UnitTypeId.RAVEN: self.raven,
        }
    
    @property
    def ordered_unit_types(self) -> List[UnitTypeId]:
        # stable sort: ties (and units out of the composition, at inf) keep the army_trainers order
        return sorted(
            self.army_trainers.keys(),
            key=self.bot.composition_manager.training_priority,
        )

    def trainer_for(self, unit_type: UnitTypeId) -> Callable[[Resources], Awaitable[Resources]]:
        """Map each UnitTypeId to its corresponding train() function."""
        if (unit_type not in self.army_trainers.keys()):
            raise ValueError(f"No trainer available for {unit_type}")

        return self.army_trainers[unit_type].train

    async def train_army(self, resources: Resources) -> Resources:
        """
        Train army units one at a time, re-sorting the priorities after each order,
        so that production is interleaved (tank, tank, thor, tank...) instead of one
        unit type filling every free building in the same frame.

        Each pass goes through the unit types by priority and stops at the first one trained.
        A type that can't be afforded marks the resource as short for the types after it
        (they don't steal its money), like the other money spenders.
        Every pass starts again from the shortages known when entering this function, so that
        a shortage caused by a lower priority type doesn't block the new first ones.
        """
        for train in self.army_trainers.values():
            train.i = 0
        minerals_short: bool = resources.minerals.short
        vespene_short: bool = resources.vespene.short

        while True:
            if (resources.is_short_both):
                return resources
            trained: bool = False
            for unit_type in self.ordered_unit_types:
                trained, resources = await self.army_trainers[unit_type].train_one(resources)
                if (trained):
                    break
            if (not trained):
                return resources
            resources = Resources.from_tuples(
                (resources.minerals.amount, minerals_short),
                (resources.vespene.amount, vespene_short),
            )