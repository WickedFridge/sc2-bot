from typing import List, Union, override

from bot.combat.micro_units.micro_unit import MicroUnit
from bot.macro.expansion import Expansion
from bot.utils.army import Army
from bot.utils.unit_supply import get_unit_supply
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from s2clientprotocol import raw_pb2 as raw_pb
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import ui_pb2 as ui_pb


class MicroMedivac(MicroUnit):
    async def unload(self, medivac: Unit):
        if (medivac.cargo_used == 0):
            return
        # unload all units at medivac position
        if (
            self.bot.raw_affects_selection is not True
            or self.bot.enable_feature_layer is not True
        ):
            medivac(AbilityId.UNLOADALLAT_MEDIVAC, medivac)
            return
        passengers: Units = Units(medivac.passengers, self.bot).sorted(
            lambda unit: (get_unit_supply(unit.type_id), unit.health_percentage),
            reverse=True
        )
        await self.unload_unit(medivac, passengers.first)

    ## This function was stolen from python-sc2 at
    ## https://github.com/BurnySc2/python-sc2/pull/108/files
    ## I have no idea how this works
    async def unload_unit(self, transporter_unit: Unit, unload_unit: Union[int, Unit]):
        assert isinstance(transporter_unit, Unit)
        assert isinstance(unload_unit, (int, Unit))
        assert hasattr(self.bot, "raw_affects_selection") and self.bot.raw_affects_selection is True
        assert hasattr(self.bot, "enable_feature_layer") and self.bot.enable_feature_layer is True
        if isinstance(unload_unit, Unit):
            unload_unit_tag = unload_unit.tag
        else:
            unload_unit_tag = unload_unit

        unload_unit_index = next(
            (index for index, unit in enumerate(transporter_unit._proto.passengers) if unit.tag == unload_unit_tag),
            None
        )

        if unload_unit_index is None:
            print(f"Unable to find unit {unload_unit} in transporter {transporter_unit}")
            return

        await self.bot.client._execute(
            action=sc_pb.RequestAction(
                actions=[
                    sc_pb.Action(
                        action_raw=raw_pb.ActionRaw(
                            unit_command=raw_pb.ActionRawUnitCommand(ability_id=0, unit_tags=[transporter_unit.tag])
                        )
                    ),
                    sc_pb.Action(
                        action_ui=ui_pb.ActionUI(
                            cargo_panel=ui_pb.ActionCargoPanelUnload(unit_index=unload_unit_index)
                        )
                    ),
                ]
            )
        )

    async def boost(self, medivac: Unit):
        available_abilities = (await self.bot.get_available_abilities([medivac]))[0]
        if (AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS in available_abilities):
            medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
    
    async def pickup(self, medivac: Unit, local_units: Units):
        # stop unloading if we are
        medivac.stop()
        await self.boost(medivac)
        units_to_pickup: Units = local_units.in_distance_between(medivac, 0, 3).sorted(key = lambda unit: unit.cargo_size, reverse = True)
        for unit in units_to_pickup:
            medivac(AbilityId.LOAD_MEDIVAC, unit)
        units_next: Units = local_units.in_distance_between(medivac, 3, 10).sorted(key = lambda unit: unit.cargo_size, reverse = True)
        if (units_next.amount == 0):
            return
        medivac.move(units_next.center.towards(units_next.closest_to(medivac)))
    
    @override
    async def safety_disengage(self, medivac: Unit) -> bool:
        if (not super().safety_disengage(medivac)):
            return False
        # Unload if we're very low on life
        if (medivac.cargo_used >= 1 and medivac.health_percentage <= 0.25):
            await self.unload(medivac)
        return True
    
    async def heal(self, medivac: Unit, local_units: Units):
        HEAL_RANGE: int = 4
        ENERGY_COST: int = 5
        
        # heal damaged ally in local army
        damaged_allies: Units = local_units.filter(
            lambda unit: (
                unit.is_biological
                and unit.health_percentage < 1
            )
        ).sorted(key = lambda unit: (unit.health_percentage, unit.distance_to(medivac) > HEAL_RANGE))

        if (damaged_allies.amount >= 1 and medivac.energy > ENERGY_COST):
            medivac(AbilityId.MEDIVACHEAL_HEAL, damaged_allies.first)
            return
        local_ground_units: Units = local_units.filter(lambda unit: unit.is_flying == False)
        
        # if everyone is fine, just position yourself properly
        if (local_ground_units.amount >= 1):
            if (medivac.distance_to(local_ground_units.center) >= 10):
                await self.boost(medivac)
            medivac.move(local_ground_units.center)
        elif (self.bot.townhalls.amount >= 1):
            await self.retreat(medivac, local_units)

    @override
    async def disengage(self, medivac: Unit, local_units: Units):
        # boost if we can
        await self.boost(medivac)
        
        if (await self.safety_disengage(medivac)):
            return
        
        # if medivac not in danger, heal the closest damaged unit
        await self.heal(medivac, local_units)
    
    @override
    async def fight(self, medivac: Unit, local_units: Units, chase: bool = False):
        # unload if we can, then move towards the closest ground unit
        
        # if our medivac is filled and can unload, unload
        if (medivac.cargo_used >= 1):
            if (self.bot.in_pathing_grid(medivac.position)):
                await self.unload(medivac)
            
            ground_allied_units: Units = local_units.filter(lambda unit: unit.is_flying == False)
            ground_enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.is_flying == False)
            ground_enemy_buildings: Units = self.bot.enemy_structures
            if (ground_allied_units.amount >= 1):
                medivac.move(medivac.position.towards(ground_allied_units.closest_to(medivac)))
            elif (ground_enemy_units.amount >= 1):
                medivac.move(medivac.position.towards(ground_enemy_units.closest_to(medivac)))
            elif (ground_enemy_buildings.amount >= 1):
                medivac.move(medivac.position.towards(ground_enemy_buildings.closest_to(medivac)))
            else:
                medivac.move(medivac.position.towards(self.bot.expansions.enemy_bases.closest_to(medivac).position))

        # if there's too many medivacs in our army, back
        army: Army = Army(local_units, self.bot)
        passengers: Units = army.passengers
        local_ground_units: Units = local_units.filter(lambda unit: unit.is_flying == False) + passengers
        local_medivacs: Units = local_units(UnitTypeId.MEDIVAC).sorted(lambda unit: (
            unit.health_percentage > 0.25,
            unit.energy_percentage > 0.25,
            unit.health_percentage,
            unit.energy_percentage
        ))
        medivacs_amount_to_back: int = max(0, local_medivacs.amount - local_ground_units.amount)
        if (medivacs_amount_to_back > 0):
            if (medivac.tag in local_medivacs.take(medivacs_amount_to_back).tags):
                await self.retreat(medivac, local_units)
                return

        # boost if we need to
        if (medivac.is_active):
            medivac_target: Point2|int = medivac.orders[0].target
            target_position: Point2|None = None
            if (isinstance(medivac_target, Point2)):
                target_position = medivac_target
            else:
                target_unit = self.bot.units.find_by_tag(medivac_target)
                if (target_unit):
                    target_position = target_unit.position
                
            if (target_position and target_position.distance_to(medivac) > 10):
                await self.boost(medivac)
        
        if (await self.safety_disengage(medivac)):
            return
        await self.heal(medivac, local_units)

    @override
    async def fight_unload(self, medivac: Unit, local_units: Units, drop_target: Point2):
        # if there's a base closer than our drop target, we attack it
        # if we don't know any enemy base, we just drop the enemy main
        closest_enemy_base: Expansion = (
            self.bot.expansions.enemy_bases.closest_to(medivac)
            if self.bot.expansions.enemy_bases.amount >= 1
            else self.bot.expansions.enemy_main
        )
        closest_enemy_building: Unit = (
            self.bot.enemy_structures.closest_to(medivac)
            if self.bot.enemy_structures.amount >= 1
            else None
        )
        
        MARGIN: int = 10
        if (closest_enemy_base.position.distance_to(medivac) < drop_target.distance_to(medivac) + MARGIN):
            drop_target = closest_enemy_base.mineral_line
        if (
            closest_enemy_building
            and closest_enemy_building.position.distance_to(medivac) < drop_target.distance_to(medivac) + MARGIN
        ):
            drop_target = closest_enemy_building.position

        # boost towards the drop target and move towards it
        await self.boost(medivac)
        medivac.move(drop_target)

        # if we're close enough, unload and fight
        DROP_DISTANCE_THRESHOLD: int = 30
        if (
            medivac.distance_to(drop_target) <= DROP_DISTANCE_THRESHOLD
            and self.bot.get_terrain_height(medivac.position) == self.bot.get_terrain_height(drop_target)
        ):
            await self.unload(medivac)

    @override
    async def attack_nearest_base(self, unit: Unit, army: Army, target: Point2):
        await self.fight(unit, army.units)

    
    @override
    async def harass(self, unit: Unit, local_units: Units, workers: Units):
        await self.fight(unit, local_units)
    
    @override
    async def kill_buildings(self, unit: Unit, local_units: Units, enemy_buildings: Units):
        if (unit.cargo_used >= 4):
            await self.fight_unload(unit, local_units, enemy_buildings.first.position)
        else:
            await self.fight(unit, local_units)
    
    @override
    async def chase_buildings(self, unit: Unit, army: Army, target: Point2):
        await self.fight(unit, army.units)
    
    @override
    async def heal_up(self, unit: Unit, local_units: Units):
        await self.unload(unit)
        await self.heal(unit, local_units)
    
    @override
    async def retreat(self, unit: Unit, local_units: Units):
        enemy_units_in_sight: Units = self.bot.enemy_units.filter(lambda enemy_unit: enemy_unit.distance_to(unit) <= 10)
        
        # Don't get in the way of flying townhalls
        flying_townhall_types: List[UnitTypeId] = [
            UnitTypeId.ORBITALCOMMANDFLYING,
            UnitTypeId.COMMANDCENTERFLYING
        ]
        local_flying_townhall: Units = self.bot.structures(flying_townhall_types).closer_than(10, unit.position)
        retreat_position = (
            self.retreat_position
            if local_flying_townhall.amount == 0
            else self.retreat_position.towards(local_flying_townhall.center, -5)
        )
        
        # unload at 2/3 of the way
        if (
            unit.distance_to(retreat_position) * 2 < unit.distance_to(self.bot.expansions.enemy_main.position)
            and enemy_units_in_sight.amount == 0
        ):
            await self.unload(unit)
        if (not await self.safety_disengage(unit) and unit.distance_to(retreat_position) > 3):                
            unit.move(retreat_position)
            if (unit.distance_to(retreat_position) > 15):
                await self.boost(unit)
        return