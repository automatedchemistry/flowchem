"""A Diode Array Detector control component."""

# class DADSwitch(FlowchemComponent):
#     def __init__(self, name: str, hw_device: FlowchemDevice):
#         """DAD Control component."""
#         super().__init__(name, hw_device)
#         self.add_api_route("/lamp", self.get_lamp, methods=["GET"])
#         self.add_api_route("/lamp", self.set_lamp, methods=["PUT"])
#

#
#     async def get_lamp(self):
#         """Lamp status."""
#         ...
#
#     async def set_lamp(self, state: bool):
#         """Lamp status."""
#         ...
#
#
# class DADControl(FlowchemComponent):
#     def __init__(self, name: str, hw_device: FlowchemDevice):
#         """NMR Control component."""
#         super().__init__(name, hw_device)
#         self.add_api_route()
#         self.add_api_route("/acquire-spectrum", self.acquire_signal, methods=["PUT"])
#         self.add_api_route("/stop", self.stop, methods=["PUT"])
#
#
#
#     async def acquire_signal(self):
#         """Acquire an ."""
#         ...
#
#     async def stop(self):
#         """Stops acquisition and exit gracefully."""
#         ...
