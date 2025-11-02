from collections.abc import Callable
from typing import Awaitable, Dict, List
from bot.combat.combat import Combat
from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.units.ghost import Ghost
from bot.units.marauder import Marauder
from bot.units.marine import Marine
from bot.units.medivac import Medivac
from bot.units.raven import Raven
from bot.units.reaper import Reaper
from bot.units.scv import Scv
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
    combat: Combat
    scv: Scv
    reaper: Reaper
    marine: Marine
    marauder: Marauder
    medivac: Medivac
    ghost: Ghost
    viking: Viking
    raven: Raven
    army_trainers: Dict[UnitTypeId, Train]
    
    def __init__(self, bot: Superbot, combat: Combat) -> None:
        self.bot = bot
        self.combat = combat
        self.scv = Scv(self)
        self.reaper = Reaper(self)
        self.marine = Marine(self)
        self.marauder = Marauder(self)
        self.medivac = Medivac(self)
        self.ghost = Ghost(self)
        self.viking = Viking(self)
        self.raven = Raven(self)
        
        self.army_trainers = {
            UnitTypeId.REAPER: self.reaper,
            UnitTypeId.MARINE: self.marine,
            UnitTypeId.MARAUDER: self.marauder,
            UnitTypeId.MEDIVAC: self.medivac,
            UnitTypeId.GHOST: self.ghost,
            UnitTypeId.VIKINGFIGHTER: self.viking,
            UnitTypeId.RAVEN: self.raven,
        }
    
    @property
    def ordered_unit_types(self) -> List[UnitTypeId]:
        unit_ratios: List[tuple[UnitTypeId, float]] = [
            (unit_id, self.bot.composition_manager.ratio_trained(unit_id)) for unit_id in self.army_trainers.keys()
        ]
        
        # sort by ratio
        unit_ratios.sort(key=lambda x: x[1])
        return [unit for unit, _ in unit_ratios]

    def trainer_for(self, unit_type: UnitTypeId) -> Callable[[Resources], Awaitable[Resources]]:
        """Map each UnitTypeId to its corresponding train() function."""
        if (unit_type not in self.army_trainers.keys()):
            raise ValueError(f"No trainer available for {unit_type}")

        return self.army_trainers[unit_type].train

    @property
    def ordered_army_trainers(self) -> List[Callable[[Resources], Awaitable[Resources]]]:
        return [self.trainer_for(unit) for unit in self.ordered_unit_types]