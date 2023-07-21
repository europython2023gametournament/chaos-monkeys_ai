# SPDX-License-Identifier: BSD-3-Clause
import dataclasses
from typing import Callable

import numpy as np

# This is your team name
CREATOR = "ChaosMonkeys"


@dataclasses.dataclass
class Stage:
    item: str
    count: int
    action: Callable


# This is the AI bot that will be instantiated for the competition
class PlayerAi:
    def __init__(self):
        self.team = CREATOR  # Mandatory attribute

        # Record the previous positions of all my vehicles
        self.previous_positions = {}
        # Record the number of tanks and ships I have at each base
        self.ntanks_def = {}
        self.tanks_def = {}
        self.ntanks_att = {}
        self.tanks_att = {}
        self.nships = {}
        self.ships = {}
        self.njets = {}

    def build_mine(self, base):
        if base.crystal > base.cost("mine"):
            base.build_mine()

    def build_tank_def(self, base):
        if base.crystal > base.cost("tank"):
            tank_uid = base.build_tank(heading=360 * np.random.random())
            # build_tank() returns the uid of the tank that was built
            self.tanks_def[base.uid].add(tank_uid)
            # Add 1 to the tank counter for this base
            self.ntanks_def[base.uid] += 1

    def build_tank_att(self, base):
        if base.crystal > base.cost("tank"):
            tank_uid = base.build_tank(heading=360 * np.random.random())
            # build_tank() returns the uid of the tank that was built
            self.tanks_att[base.uid].add(tank_uid)
            # Add 1 to the tank counter for this base
            self.ntanks_att[base.uid] += 1

    def build_ship(self, base):
        if base.crystal > base.cost("ship"):
            # build_ship() returns the uid of the ship that was built
            ship_uid = base.build_ship(heading=360 * np.random.random())
            # Add 1 to the ship counter for this base
            self.nships[base.uid] += 1
            self.ships[base.uid].add(ship_uid)

    def build_jet(self, base):
        if base.crystal > base.cost("jet"):
            # build_jet() returns the uid of the jet that was built
            jet_uid = base.build_jet(heading=360 * np.random.random())
            self.njets[base.uid] += 1

    stages = [
        Stage("mines", 2, build_mine),
        Stage("tanks_def", 8, build_tank_def),
        Stage("mines", 3, build_mine),
        Stage("ships", 1, build_ship),
        Stage("tanks_def", 9, build_tank_def),
        Stage("tanks_att", 2, build_tank_att),
        Stage("ships", 2, build_ship),
        Stage("jets", 1, build_jet),
        Stage("ships", 3, build_ship),
        Stage("tanks_def", 10, build_tank_def),
        Stage("jets", 1, build_jet),
        Stage("tanks_att", 5, build_tank_att),
    ]

    def update_vehicles(self, player_info):
        alive_tanks = []
        if "tanks" in player_info:
            for tank in player_info["tanks"]:
                alive_tanks.append(tank.uid)

        for base, tanks in self.tanks_att.items():
            tanks_to_remove = {tank for tank in tanks if tank not in alive_tanks}
            for tank in tanks_to_remove:
                tanks.remove(tank)

        for base, tanks in self.tanks_def.items():
            tanks_to_remove = {tank for tank in tanks if tank not in alive_tanks}
            for tank in tanks_to_remove:
                tanks.remove(tank)

        alive_ships = []
        if "ships" in player_info:
            alive_ships = [ship.uid for ship in player_info["ships"]]

        for base, ships in self.ships.items():
            ships_to_remove = {ship for ship in ships if ship not in alive_ships}
            for ship in ships_to_remove:
                ships.remove(ship)

    def get_next_stage(self, base) -> Callable:
        for stage in self.stages:
            if stage.item == "mines":
                if base.mines < stage.count:
                    return stage.action
            elif stage.item == "tanks_def":
                if len(self.tanks_def[base.uid]) < stage.count:
                    return stage.action
            elif stage.item == "tanks_att":
                if len(self.tanks_att[base.uid]) < stage.count:
                    return stage.action
            elif stage.item == "ships":
                if len(self.ships[base.uid]) < stage.count:
                    return stage.action
            elif stage.item == "jets":
                if self.njets[base.uid] < stage.count:
                    return stage.action
        return self.__class__.build_ship

    def run(self, t: float, dt: float, info: dict, game_map: np.ndarray):
        """
        This is the main function that will be called by the game engine.

        Parameters
        ----------
        t : float
            The current time in seconds.
        dt : float
            The time step in seconds.
        info : dict
            A dictionary containing all the information about the game.
            The structure is as follows:
            {
                "team_name_1": {
                    "bases": [base_1, base_2, ...],
                    "tanks": [tank_1, tank_2, ...],
                    "ships": [ship_1, ship_2, ...],
                    "jets": [jet_1, jet_2, ...],
                },
                "team_name_2": {
                    ...
                },
                ...
            }
        game_map : np.ndarray
            A 2D numpy array containing the game map.
            1 means land, 0 means water, -1 means no info.
        """

        # Get information about my team
        myinfo = info[self.team]

        # Controlling my bases =================================================

        # Description of information available on bases:
        #
        # This is read-only information that all the bases (enemy and your own) have.
        # We define base = info[team_name_1]["bases"][0]. Then:
        #
        # base.x (float): the x position of the base
        # base.y (float): the y position of the base
        # base.position (np.ndarray): the (x, y) position as a numpy array
        # base.team (str): the name of the team the base belongs to, e.g. ‘John’
        # base.number (int): the player number
        # base.mines (int): the number of mines inside the base
        # base.crystal (int): the amount of crystal the base has in stock
        #     (crystal is per base, not shared globally)
        # base.uid (str): unique id for the base
        #
        # Description of base methods:
        #
        # If the base is your own, the object will also have the following methods:
        #
        # base.cost("mine"): get the cost of an object.
        #     Possible types are: "mine", "tank", "ship", "jet"
        # base.build_mine(): build a mine
        # base.build_tank(): build a tank
        # base.build_ship(): build a ship
        # base.build_jet(): build a jet

        # Iterate through all my bases (vehicles belong to bases)
        for base in myinfo["bases"]:
            # If this is a new base, initialize the tank & ship counters
            if base.uid not in self.ntanks_def:
                self.ntanks_def[base.uid] = 0
                self.ntanks_att[base.uid] = 0
            if base.uid not in self.nships:
                self.nships[base.uid] = 0
            if base.uid not in self.njets:
                self.njets[base.uid] = 0

            if base.uid not in self.tanks_def:
                self.tanks_def[base.uid] = set()
            if base.uid not in self.tanks_att:
                self.tanks_att[base.uid] = set()
            if base.uid not in self.ships:
                self.ships[base.uid] = set()

            self.update_vehicles(myinfo)
            action = self.get_next_stage(base)
            print(action)
            action(self, base)

        # Try to find an enemy target
        target = None
        # If there are multiple teams in the info, find the first team that is not mine
        if len(info) > 1:
            for name in info:
                if name != self.team:
                    # Target only bases
                    if "bases" in info[name]:
                        # Simply target the first base
                        t = info[name]["bases"][0]
                        target = [t.x, t.y]

        # Controlling my vehicles ==============================================

        # Description of information available on vehicles
        # (same info for tanks, ships, and jets):
        #
        # This is read-only information that all the vehicles (enemy and your own) have.
        # We define tank = info[team_name_1]["tanks"][0]. Then:
        #
        # tank.x (float): the x position of the tank
        # tank.y (float): the y position of the tank
        # tank.team (str): the name of the team the tank belongs to, e.g. ‘John’
        # tank.number (int): the player number
        # tank.speed (int): vehicle speed
        # tank.health (int): current health
        # tank.attack (int): vehicle attack force (how much damage it deals to enemy
        #     vehicles and bases)
        # tank.stopped (bool): True if the vehicle has been told to stop
        # tank.heading (float): the heading angle (in degrees) of the direction in
        #     which the vehicle will advance (0 = east, 90 = north, 180 = west,
        #     270 = south)
        # tank.vector (np.ndarray): the heading of the vehicle as a vector
        #     (basically equal to (cos(heading), sin(heading))
        # tank.position (np.ndarray): the (x, y) position as a numpy array
        # tank.uid (str): unique id for the tank
        #
        # Description of vehicle methods:
        #
        # If the vehicle is your own, the object will also have the following methods:
        #
        # tank.get_position(): returns current np.array([x, y])
        # tank.get_heading(): returns current heading in degrees
        # tank.set_heading(angle): set the heading angle (in degrees)
        # tank.get_vector(): returns np.array([cos(heading), sin(heading)])
        # tank.set_vector(np.array([vx, vy])): set the heading vector
        # tank.goto(x, y): go towards the (x, y) position
        # tank.stop(): halts the vehicle
        # tank.start(): starts the vehicle if it has stopped
        # tank.get_distance(x, y): get the distance between the current vehicle
        #     position and the given point (x, y) on the map
        # ship.convert_to_base(): convert the ship to a new base (only for ships).
        #     This only succeeds if there is land close to the ship.
        #
        # Note that by default, the goto() and get_distance() methods will use the
        # shortest path on the map (i.e. they may go through the map boundaries).

        # Iterate through all my tanks
        if "tanks" in myinfo:
            for tank in myinfo["tanks"]:
                for base in myinfo["bases"]:
                    if tank.uid in self.tanks_def[base.uid]:
                        if 40 < tank.get_distance(base.x, base.y, shortest=True) < 50:
                            tank.set_heading(-tank.heading)
                            tank.set_vector(tank.vector * -1)
        if "tanks" in myinfo:
            for tank in myinfo["tanks"]:
                if (tank.uid in self.previous_positions) and (not tank.stopped):
                    # If the tank position is the same as the previous position,
                    # set a random heading
                    if all(tank.position == self.previous_positions[tank.uid]):
                        tank.set_heading(np.random.random() * 360.0)
                    # Else, if there is a target, go to the target
                    elif target is not None:
                        tank.goto(*target)
                # Store the previous position of this tank for the next time step
                self.previous_positions[tank.uid] = tank.position

        # Iterate through all my ships
        if "ships" in myinfo:
            for ship in myinfo["ships"]:
                if ship.uid in self.previous_positions:
                    # If the ship position is the same as the previous position,
                    # convert the ship to a base if it is far from the owning base,
                    # set a random heading otherwise
                    if all(ship.position == self.previous_positions[ship.uid]):
                        if all(
                            ship.get_distance(base.x, base.y, shortest=True) > 40
                            for team_info in info.values()
                            for base in team_info.get("bases", [])
                        ):
                            ship.convert_to_base()
                        else:
                            ship.set_heading(np.random.random() * 360.0)
                # Store the previous position of this ship for the next time step
                self.previous_positions[ship.uid] = ship.position

        # Iterate through all my jets
        if "jets" in myinfo:
            for jet in myinfo["jets"]:
                if any(
                    120 < jet.get_distance(base.x, base.y, shortest=True) < 150
                    for base in myinfo["bases"]
                ):
                    jet.set_heading(-jet.heading)
                    jet.set_vector(jet.vector * -1)
        if "jets" in myinfo:
            for jet in myinfo["jets"]:
                # Jets simply go to the target if there is one, they never get stuck
                if target is not None:
                    jet.goto(*target)
