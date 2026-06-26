"""Kit extension entry point. Wires viewport input + manipulators + panels to the controller.

CODE_REFERENCE.md S13. This is the only layer that imports ``omni.*`` / ``carb.*``.
"""
from __future__ import annotations

import omni.ext


class RoadUpToolExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        # 1. Load/attach the OpenDriveModel; build the StageGenerator (roadup.usd.stage).
        # 2. Create RoadToolController(model) (roadup.tooling.controller).
        # 3. Wire ViewportInput -> controller; ManipulatorView <- controller.manipulators().
        # 4. Register the RoadUpPanel UI.
        raise NotImplementedError

    def on_shutdown(self) -> None:
        raise NotImplementedError
