from typing import override

from bot.army_composition import composition
from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonDetachSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units

# Build origin (derived from)
# Clem vs Showtime
# HSC Finals game 2
# https://youtu.be/qYmkoMnToA0?si=czwrxVSwsK4yBo0F&t=828

class DefensiveCycloneTank(BuildOrder):
    name: BuildOrderName = BuildOrderName.DEFENSIVE_CYCLONE_TANK.value
    in_base_cc: bool = True

    @override
    def _modify_composition(self, composition: Composition) -> None:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        modified: bool = False
        if (self.bot.structures(UnitTypeId.FACTORY).ready.amount >= 1):
            modified = True
            factory_units: Units = self.bot.units([UnitTypeId.CYCLONE, UnitTypeId.SIEGETANK])
            if (factory_units.amount == 0):
                composition.set(UnitTypeId.CYCLONE, 1)
                composition.set(UnitTypeId.SIEGETANK, 0)
            else:
                composition.set(UnitTypeId.CYCLONE, 0)
                composition.set(UnitTypeId.SIEGETANK, 2)
        if (self.bot.structures(UnitTypeId.STARPORT).ready.amount >= 1):
            if (self.bot.structures(UnitTypeId.STARPORTREACTOR).amount == 0):
                composition.set(UnitTypeId.MEDIVAC, 0)
                modified = True
            if (self.bot.structures(UnitTypeId.STARPORTTECHLAB).amount == 1):
                composition.set(UnitTypeId.RAVEN, 1)
                modified = True
        return modified

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.REFINERY, 2, False)]),
            BuildOrderStep(bot, self, 'barracks Reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'factory techlab', UnitTypeId.FACTORYTECHLAB, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'Starport', UnitTypeId.STARPORT, requirements=[(UnitTypeId.FACTORYTECHLAB, 1, True)]),
            BuildOrderStep(bot, self, 'Starport techlab', UnitTypeId.STARPORTTECHLAB, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, True)]),
            BuildOrderStep(bot, self, 'Starport Reactor', UnitTypeId.STARPORTREACTOR, target_count=2, requirements=[(UnitTypeId.STARPORTTECHLAB, 2, True)]),
            # BuildOrderStep(bot, self, 'rax #2', UnitTypeId.BARRACKS, target_count=2, townhalls=2, requirements=[(UnitTypeId.FACTORYTECHLAB, 1, True)]),
            # BuildOrderStep(bot, self, 'rax techlab 1', UnitTypeId.BARRACKSTECHLAB, target_count=2, requirements=[(UnitTypeId.BARRACKS, 2, True)]),
        ]
    
        self.swap_plans = [
            AddonDetachSwap(
                bot,
                UnitTypeId.STARPORT,
                UnitTypeId.STARPORTFLYING,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.RAVEN) == False
                )
            ),
        ]

