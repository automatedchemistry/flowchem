import opcua
import logging
from time import sleep, time, asctime, localtime

from pathlib import Path
import pandas as pd

from flowchem.devices.Hamilton.ML600 import ML600, HamiltonPumpIO
from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
from flowchem.devices.Knauer.KnauerPumpValveAPI import KnauerPump, KnauerValve
from flowchem.devices.Knauer.knauer_autodiscover import autodiscover_knauer
from flowchem.devices.MettlerToledo.iCIR import FlowIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flowchem")

# SETTINGS
CURRENT_TEMPERATURE = 30

# FILES AND PATHS
WORKING_DIR = Path().home() / "Documents"
SOURCE_FILE = WORKING_DIR / "chlorination_14_05_21.csv"
assert SOURCE_FILE.exists()
# Ensure spectra folder exits
Path(WORKING_DIR / "spectra").mkdir(exist_ok=True)

# Load xp data to run
source_df = pd.read_csv(SOURCE_FILE, index_col=0)
xp_data = source_df.query(f"T == {CURRENT_TEMPERATURE}", inplace=False)
if (xp_to_run := len(xp_data)) > 0:
    print(f"{xp_to_run} points left to run at the current temperature (i.e. {CURRENT_TEMPERATURE})")
else:
    raise RuntimeError(f"No points left to run at {CURRENT_TEMPERATURE} in this experiment!")

# IR
ir_spectrometer = FlowIR(opcua.Client(url=FlowIR.iC_OPCUA_DEFAULT_SERVER_ADDRESS))
if not ir_spectrometer.is_iCIR_connected:
    raise RuntimeError("FlowIR not connected :(")

# loop A - 0.5 ml - filling with Elite11 pumping with ML600
# Thionyl chloride - filling
elite_pump_connection = PumpIO('COM5')
pump_socl2_filling = Elite11(elite_pump_connection, address=1, diameter=14.6)  # 10 mL Gastight Syringe Model 1010 TLL, PTFE Luer Lock

# Thionyl chloride - pumping
ml600_socl2_connection = HamiltonPumpIO(port="COM7")
pump_socl2_pumping = ML600(ml600_socl2_connection, syringe_volume=5)

# loop B - 5.0 ml - filling
# Hexyldecanoic acid - filling
ml600_acid_connection = HamiltonPumpIO(port="COM8")
pump_acid_pumping = ML600(ml600_acid_connection, syringe_volume=5)

# Hexyldecanoic acid - pumping
_pump_acid_mac = '00:20:4a:cd:b7:44'
available_knauer_devices = autodiscover_knauer(source_ip='192.168.1.1')
try:
    pump_acid = KnauerPump(available_knauer_devices[_pump_acid_mac])
except KeyError as e:
    raise RuntimeError("Acid pump unreachable. Is it connected and powered on?") from e

# Injection valve A
_valve_A_mac = '00:80:a3:ce:7e:c4'
valveA = KnauerValve(available_knauer_devices[_valve_A_mac])
valveA.switch_to_position("LOAD")

# Injection valve B
_valve_B_mac = '00:80:a3:ce:8e:47'
valveB = KnauerValve(available_knauer_devices[_valve_B_mac])
valveB.switch_to_position("LOAD")

# Stop loop-filling pumps and start infusion pumps

# Start infusion pumps
# Thionyl chloride - filling
pump_socl2_filling.stop()
pump_socl2_filling.infusion_rate = 0.01
pump_socl2_filling.infuse_run()

pump_acid.set_flow(0.1)
pump_acid.start_flow()



# Loop execute the points that are needed
for index, row in xp_data.iterrows():
    print(f"Applying the following conditions: tR={row['tR']}, SOCl2_eq={row['eq']}, temp={row['T']}")

    # Once experiment is performed remove it from the source CSV
    # source_df.drop(index, inplace=True)
    # source_df.to_csv(SOURCE_FILE)
