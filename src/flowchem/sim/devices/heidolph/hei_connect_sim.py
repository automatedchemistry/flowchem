"""Simulation class for Heidolph MR Hei-Connect."""

from flowchem.devices.heidolph.hei_connect import SimulatedHeiConnect


class HeiConnectSim(SimulatedHeiConnect):
    """Sim-module wrapper for SimulatedHeiConnect, following registry conventions."""
