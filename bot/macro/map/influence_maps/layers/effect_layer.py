from bot.macro.map.influence_maps.influence_map import InfluenceMap
from bot.utils.point2_functions.utils import center
from sc2.bot_ai import BotAI
from sc2.ids.effect_id import EffectId
from sc2.position import Point2

class EffectStaticData:
    radius: float
    damage: float
    ground: bool
    air: bool

    def __init__(self, radius: float, damage: float, ground: float = True, air = False):
        self.radius = radius
        self.damage = damage
        self.ground = ground
        self.air = air


class EffectLayer:
    """
    Handles temporary / persistent map effects (psistorms, ravager bile, etc).
    Each call to update() should reset and reapply active effects.
    """
    ground: InfluenceMap
    air: InfluenceMap
    effect_data: dict[str|EffectId, EffectStaticData] = {
        "KD8CHARGE": EffectStaticData(
            radius=1,
            damage=20,
        ),
        EffectId.PSISTORMPERSISTENT: EffectStaticData(
            radius=2,
            damage=23.3,
            air=True,
        ),
        EffectId.RAVAGERCORROSIVEBILECP: EffectStaticData(
            radius=1,
            damage=60,
            air=True,
        ),
        EffectId.BLINDINGCLOUDCP: EffectStaticData(
            radius=2,
            damage=30,
            air=True,
        ),
        EffectId.LURKERMP: EffectStaticData(
            radius=1,
            damage=20,
        )
    }
    
    def __init__(self, bot: BotAI):
        self.bot = bot
        self.ground = InfluenceMap(bot)
        self.air = InfluenceMap(bot)

    def reset(self):
        self.ground.map[:] = 0
        self.air.map[:] = 0

    def update_effect(self, position: Point2, data: EffectStaticData):
        if (data.ground):
            self.ground.update(position, data.radius, data.damage)
        if (data.air):
            self.air.update(position, data.radius, data.damage)
    
    def update(self):
        self.reset()
        for effect in self.bot.state.effects:
            if (effect.id not in self.effect_data):
                print(f'Error : effect {effect.id} not in effect data')
                continue

            data: EffectStaticData = self.effect_data[effect.id]
            if (len(effect.positions) > 1):
                for position in effect.positions:
                    self.update_effect(position, data)
            else:
                self.update_effect(effect.positions.pop(), data)

        