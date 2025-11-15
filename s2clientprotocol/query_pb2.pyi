from google.protobuf.message import Message
from .common_pb2 import Point2D, AvailableAbility
from .error_pb2 import ActionResult

class RequestQuery(Message):
    pathing: list[RequestQueryPathing]
    abilities: list[RequestQueryAvailableAbilities]
    placements: list[RequestQueryBuildingPlacement]
    ignore_resource_requirements: bool
    def __init__(
        self,
        pathing: list[RequestQueryPathing] = ...,
        abilities: list[RequestQueryAvailableAbilities] = ...,
        placements: list[RequestQueryBuildingPlacement] = ...,
        ignore_resource_requirements: bool = ...,
    ) -> None: ...

class ResponseQuery(Message):
    pathing: list[ResponseQueryPathing]
    abilities: list[ResponseQueryAvailableAbilities]
    placements: list[ResponseQueryBuildingPlacement]
    def __init__(
        self,
        pathing: list[ResponseQueryPathing] = ...,
        abilities: list[ResponseQueryAvailableAbilities] = ...,
        placements: list[ResponseQueryBuildingPlacement] = ...,
    ) -> None: ...

class RequestQueryPathing(Message):
    start_pos: Point2D
    unit_tag: int
    end_pos: Point2D
    def __init__(
        self,
        start_pos: Point2D = ...,
        unit_tag: int = ...,
        end_pos: Point2D = ...,
    ) -> None: ...

class ResponseQueryPathing(Message):
    distance: float
    def __init__(self, distance: float = ...) -> None: ...

class RequestQueryAvailableAbilities(Message):
    unit_tag: int
    def __init__(self, unit_tag: int = ...) -> None: ...

class ResponseQueryAvailableAbilities(Message):
    abilities: list[AvailableAbility]
    unit_tag: int
    unit_type_id: int
    def __init__(
        self,
        abilities: list[AvailableAbility] = ...,
        unit_tag: int = ...,
        unit_type_id: int = ...,
    ) -> None: ...

class RequestQueryBuildingPlacement(Message):
    ability_id: int
    target_pos: Point2D
    placing_unit_tag: int
    def __init__(
        self,
        ability_id: int = ...,
        target_pos: Point2D = ...,
        placing_unit_tag: int = ...,
    ) -> None: ...

class ResponseQueryBuildingPlacement(Message):
    result: ActionResult
    def __init__(self, result: ActionResult = ...) -> None: ...
