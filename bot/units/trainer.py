from collections.abc import Callable
from typing import Awaitable, Dict, List
from bot.combat.combat import Combat
from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.units.ghost import Ghost
from bot.units.marauder import Marauder
from bot.units.marine import Marine
from bot.units.medivac import Medivac
from bot.units.scv import Scv
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
    medivac: Medivac
    marine: Marine
    marauder: Marauder
    ghost: Ghost
    
    def __init__(self, bot: Superbot, combat: Combat) -> None:
        self.bot = bot
        self.combat = combat
        self.scv = Scv(self)
        self.medivac = Medivac(self)
        self.marine = Marine(self)
        self.marauder = Marauder(self)
        self.ghost = Ghost(self)

    # @property
    # def ordered_army_trainers(self) -> List[Callable[[Resources], Awaitable[Resources]]]:
    #     trainer_functions: List[tuple[Callable[[Resources], Awaitable[Resources]], float]] = [
    #         (self.medivac.train, self.bot.composition_manager.ratio_trained(UnitTypeId.MEDIVAC)),
    #         (self.marine.train, self.bot.composition_manager.ratio_trained(UnitTypeId.MARINE)),
    #         (self.marauder.train, self.bot.composition_manager.ratio_trained(UnitTypeId.MARAUDER)),
    #         (self.ghost.train, self.bot.composition_manager.ratio_trained(UnitTypeId.GHOST)),
    #     ]
    #     # sort by second element of tuple (the ratio)
    #     trainer_functions.sort(key=lambda x: x[1])

    #     # return only the functions, drop the ratios
    #     return [func for func, _ in trainer_functions]
    
    @property
    def ordered_unit_types(self) -> List[UnitTypeId]:
        unit_ratios: list[tuple[UnitTypeId, float]] = [
            (UnitTypeId.MARINE, self.bot.composition_manager.ratio_trained(UnitTypeId.MARINE)),
            (UnitTypeId.MARAUDER, self.bot.composition_manager.ratio_trained(UnitTypeId.MARAUDER)),
            (UnitTypeId.MEDIVAC, self.bot.composition_manager.ratio_trained(UnitTypeId.MEDIVAC)),
            (UnitTypeId.GHOST, self.bot.composition_manager.ratio_trained(UnitTypeId.GHOST)),
        ]
        # sort by ratio
        unit_ratios.sort(key=lambda x: x[1])
        return [unit for unit, _ in unit_ratios]

    def trainer_for(self, unit_type: UnitTypeId) -> Callable[[Resources], Awaitable[Resources]]:
        """Map each UnitTypeId to its corresponding train() function."""
        match unit_type:
            case UnitTypeId.MARINE:
                return self.marine.train
            case UnitTypeId.MARAUDER:
                return self.marauder.train
            case UnitTypeId.MEDIVAC:
                return self.medivac.train
            case UnitTypeId.GHOST:
                return self.ghost.train
            case _:
                raise ValueError(f"No trainer available for {unit_type}")

    @property
    def ordered_army_trainers(self) -> List[Callable[[Resources], Awaitable[Resources]]]:
        return [self.trainer_for(unit) for unit in self.ordered_unit_types]
        