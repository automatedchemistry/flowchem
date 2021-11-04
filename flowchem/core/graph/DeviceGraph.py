from __future__ import annotations

import inspect
import itertools
import json
import logging
import os
from collections import namedtuple
from pathlib import Path
from types import ModuleType
from typing import *

import jsonschema
import yaml

import flowchem.components.devices
from flowchem.exceptions import InvalidConfiguration
from flowchem.core.graph.DeviceNode import DeviceNode
from flowchem.components.stdlib import Tube
from flowchem.core.apparatus import Apparatus

# packages containing the device class definitions. Target classes should be available in the module top level.
DEVICE_MODULES = [flowchem.components.devices]

# Validation schema for graph file
SCHEMA = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "../graph/flowchem-graph-spec.schema"
)


def get_device_class_mapper(modules: Iterable[ModuleType]) -> Dict[str, type]:
    """
    Given an iterable of modules containing the device classes, return a
    dictionary Dict[device_class_name, DeviceClass]

    Args:
        modules (Iterable[ModuleType]): The modules to inspect for devices.
            Only class in the top level of each module will be extracted.
    Returns:
        device_dict (Dict[str, type]): Dict of device class names and their
            respective classes, i.e. {device_class_name: DeviceClass}.
    """
    # Get (name, obj) tuple for the top level of each modules.
    objects_in_modules = [
        inspect.getmembers(module, inspect.isclass) for module in modules
    ]

    # Return them as dict (itertools to flatten the nested, per module, lists)
    return {k: v for (k, v) in itertools.chain.from_iterable(objects_in_modules)}


def load_schema():
    """ loads the schema defining valid config file. """
    with open(SCHEMA, "r") as fp:
        schema = json.load(fp)
        jsonschema.Draft7Validator.check_schema(schema)
        return schema


Connection = namedtuple("Connection", ["from_device", "to_device", "tube"])


class DeviceGraph:
    """
    Represents the device graph.

    This borrows logic from mw.Apparatus and ChempilerGraph
    """

    _id_counter = 0

    def __init__(self, configuration, name: Optional[str] = None):
        # if given a name, then name the apparatus, else default to a sequential name
        if name is not None:
            self.name = name
        else:
            self.name = "DeviceGraph" + str(DeviceGraph._id_counter)
            DeviceGraph._id_counter += 1

        # dict of devices with names as keys
        self.device: Dict[str, Any] = {}
        # Edge list represents the network topology
        self.edge_list: List[Connection] = []

        # Save config pre-parsing for debug purposes
        self._raw_config = configuration

        # Logger
        self.log = logging.getLogger(__name__).getChild("DeviceGraph")

        # Load graph
        # self.validate(configuration)
        self.parse(configuration)

    @classmethod
    def from_file(cls, file: Union[Path, str]):
        """ Creates DeviceGraph from config file """

        file_path = Path(file)
        name = file_path.stem

        with file_path.open() as stream:
            config = yaml.safe_load(stream)

        return cls(config, name)

    def validate(self, config):
        """ Validates config syntax. """
        schema = load_schema()
        jsonschema.validate(config, schema=schema)

    def parse(self, config: Dict):
        """ Parse config and generate graph. """

        # Device mapper
        device_mapper = get_device_class_mapper(DEVICE_MODULES)
        self.log.debug(
            f"The following device classes have been found: {device_mapper.keys()}"
        )

        # Parse list of devices and create nodes
        for device_name, node_config in config["devices"].items():
            # Schema validation ensures only 1 hit here
            try:
                device_class = [
                    name for name in device_mapper.keys() if name in node_config
                ].pop()
            except IndexError as e:
                raise InvalidConfiguration(f"Node config invalid: {node_config}")

            # Object type
            obj_type = device_mapper[device_class]
            device_config = node_config[device_class]

            self.device[device_name] = DeviceNode(device_name, device_config, obj_type).device
            self.log.debug(f"Created device <{device_name}> with config: {device_config}")

        for tube_config in config["connections"].values():
            # length: str, ID: str, OD: str, material: str):
            tube = Tube(length=tube_config["length"],
                           ID=tube_config["inner-diameter"],
                           OD=tube_config["outer-diameter"],
                           material=tube_config["material"])

            # Devices
            from_device = self.device[tube_config["from"]["device"]]
            to_device = self.device[tube_config["to"]["device"]]

            # If necessary updates mapping.
            if tube_config["from"]["position"] != 0:
                from_device.mapping[from_device.name] = tube_config["from"]["position"]
            if tube_config["to"]["position"] != 0:
                to_device.mapping[from_device.name] = tube_config["to"]["position"]

            self.edge_list.append(Connection(from_device, to_device, tube))

    def to_apparatus(self) -> Apparatus:
        """
        Convert the graph to an mw.Apparatus object.
        """

        appa = Apparatus(self.name, f"Apparatus auto-generated from flowchem DeviceGraph.")
        for edge in self.edge_list:
            print(edge)
            print(edge.from_device)
            print(edge.to_device)
            print(edge.tube)

            appa.add(edge.from_device, edge.to_device, edge.tube)
        return appa

    def __repr__(self):
        return f"<DeviceGraph {self.name}>"

    def __str__(self):
        return f"DeviceGraph {self.name} with {len(self.device)} devices."

    def __getitem__(self, item):
        """
        Utility method

        DeviceGraph['name'] gives the device with that name
        DeviceGraph[class] returns a list of devices of that type
        DeviceGraph[device_instance] returns true if the object is part of the graph
        """

        # If a type is passed return devices with that type
        if isinstance(item, type):
            return [
                device
                for device in self.device.values()
                if isinstance(device, item)
            ]
        # If a string is passed return the device with that name
        elif isinstance(item, str):
            try:
                return self.device[item]
            except IndexError:
                raise KeyError(f"No component named '{item}' in {repr(self)}.")

        # a shorthand way to check if a component is in the apparatus
        elif item in self.device.values():
            return item
        else:
            raise KeyError(f"{repr(item)} is not in {repr(self)}.")


if __name__ == '__main__':
    graph = DeviceGraph.from_file("sample_config.yml")
    a = graph.to_apparatus()
    print(a)
    input()
