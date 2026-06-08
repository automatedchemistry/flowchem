"""HA Elite11 tests.

1. Update pump serial port and address belo
2. Run with `python -m pytest ./tests -m HApump` from the root folder
"""

import asyncio
import math

import pytest

from flowchem import ureg
from flowchem.devices.harvardapparatus.elite11 import Elite11


@pytest.fixture
def pump() -> Elite11:
    """Workaround for https://youtrack.jetbrains.com/issue/PY-30279/"""


@pytest.fixture(scope="session")
async def pump() -> Elite11:  # noqa
    """Change to match your hardware ;)."""
    pump = Elite11.from_config(
        port="COM4",
        syringe_volume="5 ml",
        syringe_diameter="20 mm",
    )
    await pump.initialize()
    return pump


async def move_infuse(pump):
    await pump.set_syringe_diameter("10 mm")
    await pump.set_flow_rate("1 ml/min")
    await pump.set_target_volume("1 ml")
    await pump.infuse()


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.HApump
async def test_version(pump: Elite11):
    assert "11 ELITE" in await pump.version()


@pytest.mark.HApump
async def test_is_moving(pump: Elite11):
    assert await pump.is_moving() is False
    await move_infuse(pump)
    assert await pump.is_moving() is True
    await pump.stop()


@pytest.mark.HApump
async def test_syringe_volume(pump: Elite11):
    await pump.set_syringe_volume(ureg.Quantity("10 ml"))
    assert await pump.get_syringe_volume() == "10 ml"
    await pump.set_syringe_volume(ureg.Quantity(f"{math.pi} ml"))
    vol = ureg.Quantity(await pump.get_syringe_volume()).magnitude
    assert math.isclose(vol, math.pi, abs_tol=10e-4)
    await pump.set_syringe_volume(ureg.Quantity("3e-05 ml"))
    vol = ureg.Quantity(await pump.get_syringe_volume()).magnitude
    assert math.isclose(vol, 3e-5)
    await pump.set_syringe_volume(
        ureg.Quantity("50 ml")
    )  # Leave it high for next tests


@pytest.mark.HApump
async def test_infusion_rate(pump: Elite11):
    await pump.set_syringe_volume(ureg.Quantity("10 ml"))
    await pump.set_flow_rate("5 ml/min")
    assert await pump.get_flow_rate()
    with pytest.warns(UserWarning):
        await pump.set_flow_rate("121 ml/min")
    rate = ureg.Quantity(await pump.get_flow_rate()).magnitude
    assert math.isclose(rate, 12.49, rel_tol=0.01)
    with pytest.warns(UserWarning):
        await pump.set_flow_rate("0 ml/min")
    rate = ureg.Quantity(await pump.get_flow_rate()).magnitude
    assert math.isclose(rate, 1e-05, abs_tol=1e-5)
    await pump.set_flow_rate(f"{math.pi} ml/min")
    rate = ureg.Quantity(await pump.get_flow_rate()).magnitude
    assert math.isclose(rate, math.pi, abs_tol=0.001)


@pytest.mark.HApump
async def test_force(pump: Elite11):
    await pump.set_force(10)
    assert await pump.get_force() == 10
    await pump.set_force(50.2)
    assert await pump.get_force() == 50
    assert await pump.get_force() == 50


@pytest.mark.HApump
async def test_diameter(pump: Elite11):
    await pump.set_syringe_diameter(ureg.Quantity("10 mm"))
    assert await pump.get_syringe_diameter() == "10.0000 mm"

    with pytest.warns(UserWarning):
        await pump.set_syringe_diameter(ureg.Quantity("34 mm"))

    with pytest.warns(UserWarning):
        await pump.set_syringe_diameter(ureg.Quantity("0.01 mm"))

    await pump.set_syringe_diameter(ureg.Quantity(f"{math.pi} mm"))
    dia = ureg.Quantity(await pump.get_syringe_diameter()).magnitude
    math.isclose(dia, math.pi)
