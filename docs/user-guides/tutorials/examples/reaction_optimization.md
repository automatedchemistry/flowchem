# Autonomous reaction optimization

This example demonstrates how to set up a process using flowchem. The process involves the reaction of two reagents, 
*hexyldecanoic acid*, and *thionyl chloride*, within a temperature-controlled reactor.

This process needs four electronic devices, two pumps were used to deliver the reagents. 
One pump is from [AzuraCompact](../../reference/devices/pumps/azura_compact.md), and the other is from 
Elite11 [](../../reference/devices/pumps/elite11.md). A reactor with controlled temperature was used. This reator is a component of 
the platform R2 - [R4Heater](../../reference/devices/technical/r4_heater.md). An infrared spectroscope from IR was used to analyze the 
product - [IcIR](../../reference/devices/analytics/icir.md).

:::{figure-md} Synthesis
<img src="reaction.JPG" alt="Suggestion of follow the documetation" class="bg-primary mb-1" width="100%">

**Figure 1** Automatic synthesis
:::

To gain a better understanding of the example, let's examine three different files that enabled the automation of the 
platform.

```bash
experiment_folder/
├── configuration_file.toml
├── main.py
└── run_experiment.py
```

The configuration file looks like that (`configuration_file.toml`):

```toml
[device.socl2]
type = "Elite11"
port = "COM4"
syringe_diameter = "14.567 mm"
syringe_volume = "10 ml"
baudrate = 115200

[device.hexyldecanoic]
type = "AzuraCompact"
ip_address = "192.168.1.119"
max_pressure = "10 bar"

[device.r4-heater]
type = "R4Heater"
port = "COM1"

[device.flowir]
type = "IcIR"
url = "opc.tcp://localhost:62552/iCOpcUaServer"
template = "30sec_2days.iCIRTemplate"
```

## Access API

The electronic components used in the process were accessed from a Python script `run_experiment.py`.

```python
from flowchem.client.client import get_all_flowchem_devices
# Flowchem devices
flowchem_devices = get_all_flowchem_devices()

socl2 = flowchem_devices["socl2"]["pump"]
hexyldecanoic = flowchem_devices["hexyldecanoic"]["pump"]
reactor = flowchem_devices["r4-heater"]["reactor1"]
flowir = flowchem_devices["flowir"]["ir-control"]
```

Each component has its own GET and PUT methods. The commands are written based on available methods. 
When flowchem is running, you can easily see each device's available methods through the address 
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). You can also find the methods in the 
[API documentation](../../reference/api/index.md).

The following is a description of the main `main.py` script which controls the experiment.

```python
# This package is used to read the current time and work with time management.
import time  

#Package used for optimization, more details: https://gryffin.readthedocs.io/en/latest/index.html
from gryffin import Gryffin

# This package provides logging to the Python terminal.
# and warns about errors, initialization, stage and end of the experiment.
from loguru import logger

# import devices and the main function used in the experiment.
from run_experiment import run_experiment, reactor, flowir, hexyldecanoic, socl2

# The logging of the experiment done by the loguru is saved to file xp.log
logger.add("./xp.log", level="INFO")

# load configuration before initializing the experiment
config = {
    "parameters": [
        {"name": "SOCl2_equivalent", "type": "continuous", "low": 1.0, "high": 1.5},
        {"name": "temperature", "type": "continuous", "low": 30, "high": 65},
        {"name": "residence_time", "type": "continuous", "low": 2, "high": 20},
    ],
    "objectives": [
        {"name": "product_ratio_IR", "goal": "max"},
    ],
}

# Initialize gryffin
gryffin = Gryffin(config_dict=config)
observations = []


# Initialize hardware
# Heater to r.t.
reactor.put("temperature", params={"temperature": "21"})    # -> Observe how the methods PUT is used
reactor.put("power-on")

# Start pumps with low flow rate
socl2.put("flow-rate", params={"rate": "5 ul/min"})
socl2.put("infuse")

hexyldecanoic.put("flow-rate", params={"rate": "50 ul/min"})
hexyldecanoic.put("infuse")

# Ensure iCIR is running
assert (
    flowir.get("is-connected").text == "true"
), "iCIR app must be open on the control PC"
# If IR is running we can just reuse previous experiment. Because cleaning the probe for the BG is slow

status = flowir.get("probe-status").text
if status == " Not running":
    # Start acquisition
    xp = {
        "template": "30sec_2days.iCIRTemplate",
        "name": "hexyldecanoic acid chlorination - automated",
    }
    flowir.put("experiment/start", xp)


# Run optimization for MAX_TIME
MAX_TIME = 8 * 60 * 60
start_time = time.monotonic()

while time.monotonic() < (start_time + MAX_TIME):
    # query gryffin for new conditions_to_test, 1 exploration 1 exploitation (i.e. lambda 1 and -1)
    conditions_to_test = gryffin.recommend(
        observations=observations,
        num_batches=1,
        sampling_strategies=[-1, 1],
    )

    # evaluate the proposed parameters!
    for conditions in conditions_to_test:
        # Get this from your experiment!
        conditions["product_ratio_IR"] = run_experiment(**conditions)

        logger.info(f"Experiment ended: {conditions}")

    observations.extend(conditions_to_test)
    logger.info(observations)
```

The package `run_experiment.py` is imported into the script. It's a set of functions and variables that are critical 
for the execution of the experiment, especially for infrared analysis.

```python
import time
import numpy as np
import pandas as pd
from loguru import logger
from scipy import integrate

from flowchem.client.client import get_all_flowchem_devices

# Flowchem devices
flowchem_devices = get_all_flowchem_devices()

socl2 = flowchem_devices["socl2"]["pump"]
hexyldecanoic = flowchem_devices["hexyldecanoic"]["pump"]
reactor = flowchem_devices["r4-heater"]["reactor1"]
flowir = flowchem_devices["flowir"]["ir-control"]


def calculate_flow_rates(SOCl2_equivalent: float, residence_time: float):
    """Calculate pump flow rate based on target residence time and SOCl2 equivalents.

    Stream A: hexyldecanoic acid ----|
                                     |----- REACTOR ---- IR ---- waste
    Stream B: thionyl chloride   ----|

    Args:
    ----
        SOCl2_equivalent:
        residence_time:

    Returns: dict with pump names and flow rate in ml/min

    """
    REACTOR_VOLUME = 10  # ml
    HEXYLDECANOIC_ACID = 1.374  # Molar
    SOCl2 = 13.768  # Molar

    total_flow_rate = REACTOR_VOLUME / residence_time  # ml/min

    return {
        "hexyldecanoic": (
            a := (total_flow_rate * SOCl2)
            / (HEXYLDECANOIC_ACID * SOCl2_equivalent + SOCl2)
        ),
        "socl2": total_flow_rate - a,
    }


def set_parameters(rates: dict, temperature: float):
    """Set flow rates and temperature to the reaction setup."""
    socl2.put("flow-rate", {"rate": f"{rates['socl2']} ml/min"})
    hexyldecanoic.put("flow-rate", {"rate": f"{rates['hexyldecanoic']} ml/min"})
    reactor.put("temperature", {"temperature": f"{temperature:.2f} °C"})


def wait_stable_temperature():
    """Wait until a stable temperature has been reached."""
    logger.info("Waiting for the reactor temperature to stabilize")
    while True:
        if reactor.get("target-reached").text == "true":
            logger.info("Stable temperature reached!")
            break
        else:
            time.sleep(5)


def _get_new_ir_spectrum(last_sample_id):
    while True:
        current_sample_id = int(flowir.get("sample-count").text)
        if current_sample_id > last_sample_id:
            break
        else:
            time.sleep(2)
    return current_sample_id


def get_ir_once_stable():
    """Keep acquiring IR spectra until changes are small, then returns the spectrum."""
    logger.info("Waiting for the IR spectrum to be stable")

    # Wait for first spectrum to be available
    while flowir.get("sample-count").text == 0:
        time.sleep(1)

    # Get spectrum
    previous_spectrum = pd.read_json(flowir.get("sample/spectrum-treated").text)
    previous_spectrum = previous_spectrum.set_index("wavenumber")

    last_sample_id = int(flowir.get("sample-count").text)
    while True:
        current_sample_id = _get_new_ir_spectrum(last_sample_id)

        current_spectrum = pd.read_json(flowir.get("sample/spectrum-treated").text)
        current_spectrum = current_spectrum.set_index("wavenumber")

        previous_peaks = integrate_peaks(previous_spectrum)
        current_peaks = integrate_peaks(current_spectrum)

        delta_product_ratio = abs(current_peaks["product"] - previous_peaks["product"])
        logger.info(f"Current product ratio is {current_peaks['product']}")
        logger.debug(f"Delta product ratio is {delta_product_ratio}")

        if delta_product_ratio < 0.002:  # 0.2% error on ratio
            logger.info("IR spectrum stable!")
            return current_peaks

        previous_spectrum = current_spectrum
        last_sample_id = current_sample_id


def integrate_peaks(ir_spectrum):
    """Integrate areas from `limits.in` in the spectrum provided."""
    # List of peaks to be integrated
    peak_list = np.recfromtxt("limits.in", encoding="UTF-8")

    peaks = {}
    for name, start, end in peak_list:
        # This is a common mistake since wavenumbers are plot in reverse order
        if start > end:
            start, end = end, start

        df_view = ir_spectrum.loc[
            (start <= ir_spectrum.index) & (ir_spectrum.index <= end)
        ]
        peaks[name] = integrate.trapezoid(df_view["intensity"])
        logger.debug(f"Integral of {name} between {start} and {end} is {peaks[name]}")

    # Normalize integrals
    return {k: v / sum(peaks.values()) for k, v in peaks.items()}


def run_experiment(
    SOCl2_equiv: float,
    temperature: float,
    residence_time: float,
) -> float:
    """Run one experiment with the provided conditions.

    Args:
    ----
        SOCl2_equivalent: SOCl2 to substrate ratio
        temperature: in Celsius
        residence_time: in minutes

    Returns: IR product area / (SM + product areas)

    """
    logger.info(
        f"Starting experiment with {SOCl2_equiv:.2f} eq SOCl2, {temperature:.1f} degC and {residence_time:.2f} min",
    )
    # Set stand-by flow-rate first
    set_parameters({"hexyldecanoic": "0.1 ml/min", "socl2": "10 ul/min"}, temperature)
    wait_stable_temperature()
    # Set actual flow rate once the set temperature has been reached
    pump_flow_rates = calculate_flow_rates(SOCl2_equiv, residence_time)
    set_parameters(pump_flow_rates, temperature)
    # Wait 1 residence time
    time.sleep(residence_time * 60)
    # Start monitoring IR
    peaks = get_ir_once_stable()

    return peaks["product"]


if __name__ == "__main__":
    print(get_ir_once_stable())

```

With these two files, it's possible to carry out a series of experiments in order to optimize the conditions. To see more detail on the synthesis, please go to 
[Continuous flow synthesis of the ionizable lipid ALC-0315](https://doi.org/10.1039/D3RE00630A).
