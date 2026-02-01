from typing import List
from bot.scouting.ghost_units.ghost_units import GhostUnit, GhostUnits
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId


class GhostUnitsManager:
    bot: BotAI
    ghost_units: dict[int, GhostUnit] = {}

    def __init__(self, bot: BotAI):
        self.bot = bot

    def update_ghost_units(self):
        frame = self.bot.state.game_loop
        
        # 1- Add / refresh visible enemy units
        for unit in self.bot.enemy_units:
            lifetime = 300 - unit.real_speed * 60

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
                last_seen_frame=frame,
                expiry_frame=frame + lifetime,
            )

        # 2- Remove expired ghost units
        expired = [
            tag for tag, ghost in self.ghost_units.items()
            if ghost.expiry_frame < frame
        ]
        for tag in expired:
            del self.ghost_units[tag]

        # 3- Remove ghosts that are disproven by vision
        visible_enemy_tags = {u.tag for u in self.bot.enemy_units}

        to_remove = []

        for tag, ghost in self.ghost_units.items():
            if (tag in visible_enemy_tags):
                continue  # already refreshed above

            if (self.bot.is_visible(ghost.position)):
                # We see the position but the unit is NOT there → ghost disproven
                to_remove.append(tag)

        for tag in to_remove:
            del self.ghost_units[tag]

    @property
    def assumed_enemy_units(self) -> List[GhostUnit]:
        frame = self.bot.state.game_loop

        assumed = []

        visible_tags = {u.tag for u in self.bot.enemy_units}

        for tag, ghost in self.ghost_units.items():
            if (tag in visible_tags):
                continue  # real unit already visible
            if (ghost.expiry_frame >= frame):
                assumed.append(ghost)

        return GhostUnits(self.bot, assumed)