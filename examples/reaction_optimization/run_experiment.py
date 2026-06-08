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
    socl2.put("infuse", {"rate": f"{rates['socl2']} ml/min"})
    hexyldecanoic.put("infuse", {"rate": f"{rates['hexyldecanoic']} ml/min"})
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
    SOCl2_equiv: float, temperature: float, residence_time: float
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
