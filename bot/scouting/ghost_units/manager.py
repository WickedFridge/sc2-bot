from __future__ import annotations
from typing import TYPE_CHECKING, List
from bot.scouting.ghost_units.ghost_units import GhostUnit, GhostUnits
from bot.utils.colors import ORANGE
from bot.utils.point2_functions.utils import closest_to_ally_stuff, furthest_points
from sc2.game_state import EffectData
from sc2.ids.effect_id import EffectId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
if TYPE_CHECKING:
    from bot.superbot import Superbot  # only imported for type hints

ghost_units_manager: GhostUnitsManager | None = None

class GhostUnitsManager:
    bot: Superbot
    ghost_units: dict[int, GhostUnit] = {}
    tag_counter: int = 0
    counter_offset: int = 1000000  # offset to avoid collision with real unit tags

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot

    def get_ghost_unit_by_position(self, position: Point2, type_id: UnitTypeId | None = None) -> GhostUnit | None:
        for ghost in self.ghost_units.values():
            if (ghost.position.distance_to(position) < 0.5):
                if (type_id is None or ghost.type_id == type_id):
                    return ghost
        return None

    def add_lurker_ghosts(self) -> None:
        frame = self.bot.state.game_loop
        lifetime: int = 300
        spines: List[EffectData] = [effect for effect in self.bot.state.effects if effect.id == EffectId.LURKERMP]
        for effect in spines:
            spines_extremities: List[Point2] = furthest_points(list(effect.positions))
            possible_lurker_positions: List[Point2] = []
            possible_lurker_positions.append(spines_extremities[0].towards(spines_extremities[1], -1))
            possible_lurker_positions.append(spines_extremities[1].towards(spines_extremities[0], -1))
            ghost_lurker: GhostUnit | None
            for position in possible_lurker_positions:
                ghost_lurker = self.get_ghost_unit_by_position(position, type_id=UnitTypeId.LURKERMPBURROWED)
                if (ghost_lurker is not None):
                    ghost_lurker.expiry_frame = round(frame + lifetime)
                    break

            if (ghost_lurker is None):
                assumed_lurker_position: Point2 = closest_to_ally_stuff(self.bot, possible_lurker_positions)
                self.tag_counter += 1
                tag: int = self.tag_counter + self.counter_offset  # offset to avoid collision with real unit tags
                self.ghost_units[tag] = GhostUnit(
                    tag=tag,
                    position=assumed_lurker_position,
                    type_id=UnitTypeId.LURKERMPBURROWED,
                    radius=2,
                    ground_dps=12.87,
                    ground_range=6,
                    air_dps=0,
                    air_range=0,
                    real_speed=0,
                    health=125,
                    health_max=125,
                    health_percentage=1.0,
                    shield=0,
                    shield_max=0,
                    shield_percentage=0.0,
                    energy=0,
                    energy_max=0,
                    energy_percentage=0.0,
                    is_flying=False,
                    is_armored=True,
                    can_attack=True,
                    can_attack_ground=True,
                    can_attack_air=False,
                    is_visible=False,
                    is_cloaked=False,
                    last_seen_frame=frame,
                    expiry_frame=round(frame + lifetime),
                )
                self.tag_counter += 1

    def update_ghost_units(self):
        frame = self.bot.state.game_loop
        # 1- Add / refresh visible enemy units
        for unit in self.bot.enemy_units:
            lifetime = 300 - unit.real_speed * 60

            potential_ghost: GhostUnit | None = self.get_ghost_unit_by_position(unit.position, type_id=unit.type_id)
            if (potential_ghost is not None and potential_ghost.tag != unit.tag):
                del self.ghost_units[potential_ghost.tag]

            self.ghost_units[unit.tag] = GhostUnit(
                tag=unit.tag,
                type_id=unit.type_id,
                position=unit.position,
                radius=unit.radius,
                ground_dps=unit.ground_dps,
                ground_range=unit.ground_range,
                air_dps=unit.air_dps,
                air_range=unit.air_range,
                real_speed=unit.real_speed,
                health=unit.health,
                health_max=unit.health_max,
                health_percentage=unit.health_percentage,
                shield=unit.shield,
                shield_max=unit.shield_max,
                shield_percentage=unit.shield_percentage,
                energy=unit.energy,
                energy_max=unit.energy_max,
                energy_percentage=unit.energy_percentage,
                is_flying=unit.is_flying,
                is_armored=unit.is_armored,
                can_attack=unit.can_attack,
                can_attack_ground=unit.can_attack_ground,
                can_attack_air=unit.can_attack_air,
                is_visible=unit.is_visible,
                is_cloaked=unit.is_cloaked,
                last_seen_frame=frame,
                expiry_frame=round(frame + lifetime),
            )

            
        # 1.5- Special case - add lurkers based on lurker spines
        self.add_lurker_ghosts()

        # 2- Remove expired ghost units
        expired = [
            tag for tag, ghost in self.ghost_units.items()
            if ghost.expiry_frame < frame
        ]
        for tag in expired:
            del self.ghost_units[tag]

        # 3- Remove ghosts that are disproven by vision + detection
        visible_enemy_tags = {u.tag for u in self.bot.enemy_units}

        to_remove = []

        for tag, ghost in self.ghost_units.items():
            if (tag in visible_enemy_tags):
                continue  # already refreshed above

            if (self.bot.is_visible(ghost.position)):
                if (self.bot.map.influence_maps.detection.detected[ghost.position] == 1):
                    # Vision + detection → unit truly not present
                    to_remove.append(tag)
                else:
                    # Vision but no detection → unit may be burrowed or cloaked
                    ghost.is_possibly_hidden = True

        for tag in to_remove:
            del self.ghost_units[tag]

    def remove_by_tag(self, tag: int):
        if (tag not in self.ghost_units.keys()):
            return
        del self.ghost_units[tag]
    
    @property
    def assumed_enemy_units(self) -> GhostUnits:
        frame = self.bot.state.game_loop

        assumed = []

        visible_tags = {u.tag for u in self.bot.enemy_units}

        for tag, ghost in self.ghost_units.items():
            if (tag in visible_tags):
                continue  # real unit already visible
            if (ghost.expiry_frame >= frame):
                assumed.append(ghost)

        return GhostUnits(self.bot, assumed)
    
def get_ghost_units(bot: Superbot) -> GhostUnitsManager:
    global ghost_units_manager
    if (ghost_units_manager is None):
        ghost_units_manager = GhostUnitsManager(bot)
    return ghost_units_manager