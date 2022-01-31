""" Module that defines the base class Part and Actuator.

Part inherits from Entity, and is used to create different body parts
of an agent. Parts are visible and movable by default.

Examples on how to add Parts to an agent can be found
in simple_playgrounds/agents/agents.py
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Dict, List, Optional, TYPE_CHECKING, Tuple, Union

import pymunk
from simple_playgrounds import playground

from simple_playgrounds.agent.controller import (
    Command,
    Controller,
    ContinuousController,
    DiscreteController
)
from simple_playgrounds.common.definitions import (
    CollisionTypes,
    PymunkCollisionCategories,
)
from simple_playgrounds.entity.embodied.interactive import AnchoredInteractive
from simple_playgrounds.entity.embodied.physical import PhysicalEntity

if TYPE_CHECKING:
    from simple_playgrounds.agent.agent import Agent
    from simple_playgrounds.entity.embodied.embodied import EmbodiedEntity
    from simple_playgrounds.common.position_utils import CoordinateSampler, Coordinate, Trajectory
    from simple_playgrounds.playground.playground import Commands
    _Base = EmbodiedEntity
else:
    _Base = object


CommandDict = Dict[Command, Union[float, int]]


class Part(_Base):
    """
    Mixin to transform an embodied entity into a Part.
    Parts can be controlled, and sensors can be attached to them.
    """

    def __init__(self, agent: Agent, **kwargs):

        self._agent = agent

        # Add physical motors if needed
        self._controllers: List[Controller] = self._set_controllers(**kwargs)

        self._agent.add_part(self)
        
        super().__init__(**kwargs)

    def _set_pm_collision_type(self):
        self._pm_shape.collision_type = CollisionTypes.PART

    @abstractmethod
    def _set_controllers(self, **kwargs) -> List[Controller]:
        ...

    @abstractmethod
    def apply_commands(self, **kwargs):
        ...

    @property
    def agent(self):
        return self._agent

    @property
    def name(self):
        return self._name

    @property
    def global_name(self):
        return self._agent.name + '_' + self._name

    @property
    def controllers(self):
        return self._controllers
   
    #############
    # Methods for Playground
    #############

    def pre_step(self, **_):
        for controller in self._controllers:
            controller.pre_step()

    
class Platform(Part, PhysicalEntity, ABC):

    def __init__(self, agent: Agent, **kwargs):
        super().__init__(agent=agent, **kwargs)

    def _set_initial_coordinates(
        self,
        initial_coordinates: Optional[
            Union[Coordinate, CoordinateSampler, Trajectory]] = None,
        allow_overlapping: bool = True,
        **_,
    ):
        
        if not initial_coordinates:

            if not self._playground.initial_agent_coordinates:
                raise ValueError('Initial coordinates must be set')
            initial_coordinates = self._playground.initial_agent_coordinates
            
        super()._set_initial_coordinates(initial_coordinates=initial_coordinates, allow_overlapping=allow_overlapping, **_)


class AnchoredPart(Part, PhysicalEntity, ABC):

    def __init__(self,
                 anchor: Part,
                 pivot_position_on_part: Union[Tuple[float, float], pymunk.Vec2d],
                 pivot_position_on_anchor: Union[Tuple[float, float], pymunk.Vec2d],
                 relative_angle: float,
                 rotation_range: float,
                 **kwargs):

        self._anchor = anchor

        self._anchor_point = pymunk.Vec2d(*pivot_position_on_anchor)
        self._part_point = pymunk.Vec2d(*pivot_position_on_part)
        self._angle_offset = relative_angle
        self._rotation_range = rotation_range

        init_coord = self._get_relative_coordinates()

        super().__init__(agent=anchor.agent,
                         playground=anchor.playground,
                         initial_coordinates=init_coord,
                         **kwargs)
        
        self._attach_to_anchor()
        

    def relative_position(self):

        return (self.position - self._anchor.position).rotated(
                -self._anchor.angle)

    def relative_angle(self):

        return self.angle - self._anchor.angle

    def _get_relative_coordinates(self):
        """
        Calculates the position of a Part relative to its Anchor.
        Sets the position of the Part.
        """

        position = self._anchor.position\
            + self._anchor_point.rotated(self._anchor.angle)\
            - self._part_point.rotated(
                self._anchor.angle + self._angle_offset)
       
        angle = self._anchor.pm_body.angle + self._angle_offset

        return position, angle

    def _attach_to_anchor(self):

        # Create joint to attach to anchor
        self._joint = pymunk.PivotJoint(self._anchor.pm_body, self.pm_body,
                                        self._anchor_point, self._part_point)
        self._joint.collide_bodies = False
        self._limit = pymunk.RotaryLimitJoint(
            self._anchor.pm_body, self._pm_body,
            self._angle_offset - self._rotation_range / 2,
            self._angle_offset + self._rotation_range / 2)

        self._motor = pymunk.SimpleMotor(self._anchor.pm_body, self.pm_body, 0)


class InteractivePart(Part, AnchoredInteractive):

    def __init__(self, anchor: Part, **kwargs):

        super().__init__(agent=anchor.agent, anchor=anchor, **kwargs)

    def relative_position(self):

        return (self.position - self._anchor.position).rotated(
                -self._anchor.angle)

    def relative_angle(self):

        return self.angle - self._anchor.angle


# class PhysicalPart(Part, PhysicalEntity, ABC):

#     def __init__(self, **kwargs):

#         Part.__init__(**kwargs)

#         if self._anchor:
#             # Move to position, then attach
#             self._set_relative_coordinates(**kwargs)
#             self._anchor_point, self._part_point, self._angle_offset = self._attach_to_anchor(**kwargs)
    
#     def _attach_to_anchor(self,
#                           anchor_point: Union[pymunk.Vec2d, Tuple[float, float]],
#                           part_point: Union[pymunk.Vec2d, Tuple[float, float]],
#                           rotation_range: float,
#                           angle_offset: float = 0):

#         assert self._anchor

#         # convert to point 2d
#         anchor_point = pymunk.Vec2d(*anchor_point)
#         part_point = pymunk.Vec2d(*part_point)

#         # Create joint to attach to anchor
#         self._joint = pymunk.PivotJoint(self._anchor.pm_body, self.pm_body,
#                                        anchor_point, part_point)  
#         self._joint.collide_bodies = False
#         self._limit = pymunk.RotaryLimitJoint(
#             self._anchor.pm_body, self._pm_body,
#             angle_offset - rotation_range / 2,
#             angle_offset + rotation_range / 2)

#         self._motor = pymunk.SimpleMotor(self._anchor.pm_body, self.pm_body, 0)

#         return anchor_point, part_point, angle_offset
        
#     def _set_relative_coordinates(self):
#         """
#         Calculates the position of a Part relative to its Anchor.
#         Sets the position of the Part.
#         """

#         assert self._anchor
#         self._pm_body.position = self._anchor.position\
#             + self._anchor_point.rotated(self._anchor.angle)\
#             - self._part_point.rotated(
#                 self._anchor.angle + self._angle_offset)
       
#         self._pm_body.angle = self._anchor.pm_body.angle + self._angle_offset

#     def reset(self):
#         pass
#     def reindex_shapes(self):
#         assert self._playground
#         self._playground.space.reindex_shapes_for_body(self._pm_body)

#     def _set_pm_collision_type(self):
#         self._pm_shape.collision_type = CollisionTypes.PART


# class InteractivePart(PartMixin, InteractiveEntity, ABC):

#     def _set_pm_collision_type(self):
#         self._pm_shape.collision_type = CollisionTypes.PART
