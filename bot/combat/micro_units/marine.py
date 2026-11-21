import math
from typing import Optional, Set, override

from bot.combat.micro_units.bio_unit import MicroBioUnit
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.utils.army import Army
from sc2.unit import Unit
from sc2.units import Units


class MicroMarine(MicroBioUnit):

    @override
    async def retreat(self, marine: Unit, local_units: Units):
        """
        1. Closest base needing defense (bunker, or detected burrowed unit to clean) that lacks defenders
           (retreating marines spill into them until they're filled)
        2. If every base with a defensive structure is defended, the base with the worst enemy/own army ratio
        3. Otherwise, default retreat position
        """
        if (self.bot.townhalls.amount == 0):
            return

        # 1. garrison the closest undefended base, without regrouping with the army on the way
        # (the marine doesn't count itself, so it stays at a base as long as it's needed there)
        undefended_bases: Expansions = self.bot.expansions.taken.filter(
            lambda expansion: expansion.needs_defense and not expansion.is_defended_without(marine)
        )
        if (undefended_bases.amount >= 1):
            closest_base: Expansion = undefended_bases.sorted(
                lambda expansion: marine.distance_to(expansion.retreat_position)
            ).first
            await self.retreat_to(marine, local_units, closest_base.retreat_position, regroup=False)
            return

        # 2. every base is defended: back up the one in the worst shape
        weakest_base: Optional[Expansion] = self.weakest_base(self.bot.expansions.taken.with_defensive_structure, local_units)
        if (weakest_base is not None):
            await self.retreat_to(marine, local_units, weakest_base.retreat_position)
            return

        # 3. default retreat position
        await self.retreat_to(marine, local_units, self.retreat_position)

    def weakest_base(self, bases: Expansions, local_units: Units) -> Optional[Expansion]:
        """
        Base with the worst enemy/own army ratio, None if no fighting enemy is around any of them.
        The retreating army isn't counted, or it would leave a base as soon as it reaches it.
        """
        army_tags: Set[int] = local_units.tags
        weakest: Optional[Expansion] = None
        worst_ratio: float = 0
        for expansion in bases:
            structure: Optional[Unit] = expansion.defending_structure
            if (structure is None or expansion.local_enemy_supply == 0):
                continue
            own_units: Units = expansion.local_units.tags_not_in(army_tags)
            own_units.append(structure)
            own_supply: float = Army(own_units, self.bot).weighted_supply
            ratio: float = expansion.local_enemy_supply / own_supply if own_supply > 0 else math.inf
            if (weakest is None or ratio > worst_ratio):
                weakest = expansion
                worst_ratio = ratio
        return weakest
