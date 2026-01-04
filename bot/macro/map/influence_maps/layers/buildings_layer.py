import math
from operator import pos
from attr import dataclass
from rpds import List
from bot.macro.map.influence_maps.influence_map import InfluenceMap
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from .....utils.unit_tags import add_ons, production, production_flying

@dataclass(frozen=True)
class BuildingTile:
    blocked: bool
    reserved_for: set[UnitTypeId] | None

ADDON_RADIUS = 1
DEPOT_RADIUS = 1
PRODUCTION_RADIUS = 1.5
BUNKER_RADIUS = 1.5
CC_RADIUS = 2.5

class BuildingLayer:
    bot: BotAI
    occupancy: InfluenceMap
    reservations: dict[Point2, set[UnitTypeId]]
    _grounded_buildings: set[int] = set()
    
    def __init__(self, bot: BotAI):
        self.bot = bot
        self.occupancy = InfluenceMap(bot)
        self.occupancy.map[:] = 1.0  # All buildable at start
        self.reservations = {}

    def _initialize_static_blockers(self) -> None:
        # Minerals
        for mineral in self.bot.mineral_field:
            origin, size = self._get_footprint(mineral)
            self.block_area(origin, size)

        # Geysers
        for geyser in self.bot.vespene_geyser:
            origin, size = self._get_footprint(geyser)
            self.block_area(origin, size)

        # Destructibles
        for rock in self.bot.destructables:
            if rock.radius > 0:
                origin, size = self._get_footprint(rock)
                self.block_area(origin, size)

        # Expansions
        for expansion_position in self.bot.expansion_locations_list:
            minerals: Units = self.bot.mineral_field.closer_than(10, expansion_position)
            vespene_geysers: Units = self.bot.vespene_geyser.closer_than(10, expansion_position)
            # clear the building grid for the expansion
            for mineral in minerals + vespene_geysers:
                selected_positions: List[Point2] = [expansion_position, mineral.position]
                # draw the pathing grid between the two selected units
                
                min_x, max_x = sorted([pos.x for pos in selected_positions])
                min_y, max_y = sorted([pos.y for pos in selected_positions])

                start_x = math.ceil(min_x) - 0.5
                end_x = math.floor(max_x) + 0.5
                start_y = math.ceil(min_y) - 0.5
                end_y = math.floor(max_y) + 0.5

                x = start_x
                while x <= end_x:
                    y = start_y
                    while y <= end_y:
                        self.reserve_tile(Point2((x, y)).rounded, set([UnitTypeId.MISSILETURRET]))
                        y += 1.0
                    x += 1.0
            self.reserve_cc(expansion_position)

        # Main base wall
        for depot_position in self.bot.main_base_ramp.corner_depots:
            self.reserve_depot(depot_position)
        self.reserve_production(self.bot.main_base_ramp.barracks_correct_placement)

    def _initialize_existing_structures(self) -> None:
        for structure in self.bot.structures:
            self.on_building_created(structure)
    
    def initialize(self) -> None:
        self._initialize_static_blockers()
        self._initialize_existing_structures()

    def update(self):
        for unit in self.bot.structures:
            if (not unit.is_ready):
                continue

            tag: int = unit.tag

            # addons - should block tiles around it for production buildings
            if (unit.type_id in add_ons):
                production_position: Point2 = unit.position - Point2((2.5, -0.5))
                if (production_position.rounded not in self.reservations):
                    self.reserve_production(production_position)

            # Flying building: should NOT block
            if (unit.is_flying):
                if (tag in self._grounded_buildings):
                    self.on_building_destroyed(unit)
                    self._grounded_buildings.remove(tag)

            # Grounded building: SHOULD block
            else:
                if (tag not in self._grounded_buildings):
                    self.on_building_created(unit)
                    self._grounded_buildings.add(tag)

    def get_tile(self, pos: Point2) -> BuildingTile:
        pos = pos.rounded
        blocked = self.occupancy[pos] <= 0.0
        reserved = self.reservations.get(pos)
        return BuildingTile(blocked, reserved)
    
    def is_free(self, pos: Point2) -> bool:
        pos = pos.rounded
        return self.occupancy[pos] > 0.0
    
    def can_build(self, pos: Point2, unit_type: UnitTypeId) -> bool:
        pos = pos.rounded

        # 1) Hard blocked
        if (self.occupancy[pos] <= 0.0):
            return False

        # 2) Reservation check
        reserved_for = self.reservations.get(pos)
        if (reserved_for is not None and unit_type not in reserved_for):
            return False

        # 3) Engine placement checks
        return (
            self.bot.in_placement_grid(pos)
            and self.bot.in_pathing_grid(pos)
        )

    def _get_footprint(self, unit: Unit) -> tuple[Point2, int]:
        
        radius: float = (
            unit.footprint_radius
            if unit.footprint_radius and unit.footprint_radius > 0
            else unit.radius
        )

        if unit.type_id in {
            UnitTypeId.COMMANDCENTERFLYING,
            UnitTypeId.ORBITALCOMMANDFLYING,
        }:
            radius = CC_RADIUS

        if unit.type_id in production_flying:
            radius = PRODUCTION_RADIUS
        
        if unit.type_id in add_ons:
            radius = ADDON_RADIUS

        size: int = int(round(radius * 2))
        half: float = size / 2

        position: Point2 = (
            unit.position.rounded
            if size % 2 == 0
            else unit.position.rounded_half
        )

        origin = Point2((position.x - half, position.y - half))
        return origin, size
    
    def block_area(self, origin: Point2, size: int) -> None:
        ox = int(origin.x)
        oy = int(origin.y)

        self.occupancy.map[
            oy : oy + size,
            ox : ox + size
        ] = 0.0
    
    def unblock_area(self, origin: Point2, size: int) -> None:
        ox = int(origin.x)
        oy = int(origin.y)
        
        self.occupancy.map[
            oy : oy + size,
            ox : ox + size
        ] = 1.0

    def reserve_tile(self, pos: Point2, unit_types: set[UnitTypeId]) -> None:
        self.reservations[pos.rounded] = unit_types
    
    def unreserve_tile(self, pos: Point2) -> None:
        self.reservations.pop(pos.rounded, None)
    
    def reserve_area(self, origin: Point2, size: int, unit_types: set[UnitTypeId]):
        ox = int(origin.x)
        oy = int(origin.y)
        size = int(size)

        for x in range(ox, ox + size):
            for y in range(oy, oy + size):
                self.reservations[Point2((x, y)).rounded] = unit_types
    
    def unreserve_area(self, origin: Point2, size: int) -> None:
        ox = int(origin.x)
        oy = int(origin.y)
        size = int(size)

        for y in range(oy, oy + size):
            for x in range(ox, ox + size):
                self.reservations.pop(Point2((x, y)).rounded, None)
    
    def reserve_cc(self, pos: Point2) -> None:
        size = CC_RADIUS * 2
        origin = pos.rounded - Point2((2, 2))

        self.reserve_area(
            origin,
            size,
            {
                UnitTypeId.COMMANDCENTER,
                UnitTypeId.ORBITALCOMMAND,
                UnitTypeId.PLANETARYFORTRESS,
            },
        )
    
    def reserve_depot(self, pos: Point2) -> None:
        size = DEPOT_RADIUS * 2
        origin = pos.rounded - Point2((0.5, 0.5))
        
        self.reserve_area(
            origin,
            size,
            {UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED},
        )
    
    def reserve_production(self, pos: Point2) -> None:
        size = PRODUCTION_RADIUS * 2
        origin = pos.rounded - Point2((1, 1))
        addon_position = pos.rounded + Point2((2.5, -0.5))
        self.reserve_area(
            origin,
            size,
            set(production),
        )
        self.reserve_area(
            addon_position,
            2 * ADDON_RADIUS,
            set(add_ons),
        )
    
    def reserve_bunker(self, pos: Point2) -> None:
        size = BUNKER_RADIUS * 2
        origin = pos.rounded - Point2((1, 1))
        self.reserve_area(
            origin,
            size,
            {UnitTypeId.BUNKER},
        )

    
    def on_building_created(self, unit: Unit) -> None:
        origin, size = self._get_footprint(unit)
        self.block_area(origin, size)

        if (unit.type_id in production + production_flying):
            addon_origin: Point2 = unit.add_on_position.rounded - Point2((1, 1))
            self.reserve_area(addon_origin, 2 * ADDON_RADIUS, set(add_ons))

    def on_building_destroyed(self, unit: Unit) -> None:
        origin, size = self._get_footprint(unit)
        self.unblock_area(origin, size)

        if (unit.type_id in production + production_flying):
            addon_origin: Point2 = unit.add_on_position.rounded - Point2((1, 1))
            self.unreserve_area(addon_origin, 2 * ADDON_RADIUS)