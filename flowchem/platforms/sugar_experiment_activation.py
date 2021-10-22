from time import sleep
from flowchem.devices.Petite_Fleur_chiller import Huber
import queue
from threading import Thread
from datetime import datetime
from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
from flowchem.devices.Knauer.HPLC_control import ClarityInterface
from flowchem.devices.Knauer.KnauerPumpValveAPI import KnauerPump
from flowchem.miscellaneous_helpers.folder_listener import FileReceiver, ResultListener
from flowchem.devices.Hamilton.ML600 import HamiltonPumpIO, ML600
import logging
from flowchem.constants import flowchem_ureg
from numpy import array, sum

# TODO combining the sample name with the commit hash would make the experiment even more traceable. probably a good idea...

# this experiment hold


class ExperimentConditions:
    """This is actively changed, either by human or by optimizer. Goes into the queue.
    When the conditions are taken from the queue, a FlowConditions object is derived from ExperimentCondition.
    ExperimentConditions has to be dropped into a database, eventually, with analytic results and the optimizer activated"""

    # fixed, only changed for a new experiment sequence (if stock solution changes)
    _stock_concentration_donor = 0.1 * flowchem_ureg.molar
    _stock_concentration_activator = 1 * flowchem_ureg.molar
    _stock_concentration_quencher = 1 * flowchem_ureg.molar
    # how many reactor volumes until steady state reached
    _reactor_volumes = 3
    _quencher_eq_to_activator = 2

    # could always be initialised as starting condition and adjusted by optimizer/list. Or be initialised as the to use_condition
    def __init__(self, residence_time_in_seconds=60, activator_equivalents=1.5, temperature_in_celsius=25):
        # mutable
        self.residence_time = residence_time_in_seconds * flowchem_ureg.second  # sec
        self.concentration_donor = self._stock_concentration_donor
        self.activator_equivalents = activator_equivalents
        self._quencher_equivalents = self._quencher_eq_to_activator * self.activator_equivalents
        self.temperature = flowchem_ureg.Quantity(temperature_in_celsius, flowchem_ureg.celsius)

        self.experiment_finished = False

    @property
    def stock_concentration_donor(self):
        return self._stock_concentration_donor

    @property
    def stock_concentration_activator(self):
        return self._stock_concentration_activator

    @property
    def stock_concentration_quencher(self):
        return self._stock_concentration_quencher

    @property
    def reactor_volumes(self):
        return self._reactor_volumes

    @property
    def quencher_equivalents(self):
        return self._quencher_equivalents


class FlowConditions:
    """From  experiment conditions, flow conditions can be derived, which happens right before each experiment.
    Basically, just to separate off redundant data.
    Links Experiment Conditions to platform.
    All private parameters are only internally needed for calculation (and maybe as checkpoints for simpler testing).
    """

    # these can be calculated, from each pump 'package', the flow rate should be the same I suppose
    def __init__(self, experiment_conditions: ExperimentConditions,
                 flow_platform: dict):  # for now, the flowplatform is handed in as a manually written dict and abstraction still low

        self.experiment_id = round(datetime.timestamp(datetime.now()))

        # better readability
        self.platform_volumes = flow_platform['internal_volumes']

        self._concentration_donor = experiment_conditions.concentration_donor
        self._concentration_activator = experiment_conditions.stock_concentration_activator
        self._concentration_quencher = experiment_conditions.stock_concentration_quencher

        # This is actually not needed -> the activator will always be neat / at some specific concentration
        self._total_flow_rate = self.get_flow_rate(self.platform_volumes['volume_reactor'],
                                                   experiment_conditions.residence_time)


        self.activator_flow_rate, self.donor_flow_rate = self.get_individual_flow_rate(self._total_flow_rate,
                                                                                       concentrations=(self._concentration_activator.magnitude, self._concentration_donor.magnitude,), equivalents=(experiment_conditions.activator_equivalents, 1,))
        #TODO seem very high, check this, probably due to wrong unit conversion
        self.activator_flow_rate = self.activator_flow_rate.to(flowchem_ureg.milliliter / flowchem_ureg.minute)
        self.donor_flow_rate = self.donor_flow_rate.to(flowchem_ureg.milliliter / flowchem_ureg.minute)

        # TODO watch out, now the quencher equivalents are based on donor, I think
        self.quencher_flow_rate = self.get_flowrate_added_stream(self._concentration_donor, self.donor_flow_rate, self._concentration_quencher, experiment_conditions._quencher_equivalents)

        self.temperature = experiment_conditions.temperature

        # Todo in theory not that simple anymore if different flowrates
        self._time_start_till_end = ((self.platform_volumes['dead_volume_before_reactor'] +
                                     self.platform_volumes['volume_mixing'] +
                                     self.platform_volumes['volume_reactor']) / self._total_flow_rate +
                                     (self.platform_volumes['dead_volume_to_HPLC'] / (self._total_flow_rate +
                                                                                      self.quencher_flow_rate))).to(flowchem_ureg.second)

        self.steady_state_time = (self._time_start_till_end + experiment_conditions.residence_time *
                                  (experiment_conditions.reactor_volumes-1)).to(flowchem_ureg.second)

    def get_flow_rate(self, relevant_volume: float, residence_time: int):
        return (relevant_volume / residence_time).to(flowchem_ureg.milliliter / flowchem_ureg.minute)

    #TODO for now concentration needs to go in alway in the same dimension, and as float
    def get_individual_flow_rate(self, target_flow_rate: float, equivalents: tuple = (), concentrations: tuple = ()):
        """
        Give as many inputs as desired, output will be in same order as input and hold required flowrates
        """

        normalised_flow_rates = array(equivalents) / array(concentrations)
        sum_of_normalised_flowrates = sum(normalised_flow_rates)
        correction_factor = target_flow_rate / sum_of_normalised_flowrates
        return tuple(normalised_flow_rates * correction_factor)

    def get_flowrate_added_stream(self, concentration_reference_stream:float, flowrate_reference_stream:float,
                                  concentration_added_stream:float, equivalents_added_stream:float):
        return (concentration_reference_stream*flowrate_reference_stream*equivalents_added_stream)/concentration_added_stream


class FlowProcedure:

    def __init__(self, platform_graph: dict):
        self.pumps = platform_graph['pumps']
        self.hplc: ClarityInterface = platform_graph['HPLC']
        self.chiller: Huber = platform_graph['chiller']

    def individual_procedure(self, flow_conditions: FlowConditions):
        # TODO also here, for now this is a workaround for ureg.
        self.chiller.set_temperature(flow_conditions.temperature.magnitude)
        self.chiller.start()

        while (abs(self.chiller.get_temperature()) - abs(flow_conditions.temperature.magnitude)) > 2:
            sleep(10)
            print('Chiller waiting for temperature')

        # set all flow rates
        self.pumps['donor'].infusion_rate = flow_conditions.donor_flow_rate
        self.pumps['quench'].set_flow = flow_conditions.quencher_flow_rate

        self.pumps['donor'].run()
        self.pumps['activator'].deliver_from_pump(flow_conditions.activator_flow_rate)
        self.pumps['quench'].start_flow()

        # start timer
        sleep(flow_conditions.steady_state_time)

#        self.hplc.set_sample_name(flow_conditions.experiment_id)
#        self.hplc.run()

        # timer is over, start
        self.pumps['donor']. stop()
        self.pumps['activator'].stop()
        self.pumps['activator'].refill_syringe(4, 1)



    def get_platform_ready(self):
        """Here, code is defined that runs once to prepare the platform. These are things like switching on HPLC lamps,
        sending the hplc method"""
        # prepare HPLC

#        self.hplc.exit()
#        self.hplc.switch_lamp_on()  # address and port hardcoded
#        self.hplc.open_clarity_chrom("admin", config_file=r"C:\ClarityChrom\Cfg\automated_exp.cfg ",
#                                     start_method=r"D:\Data2q\sugar-optimizer\autostartup_analysis\autostartup_005_Sugar-c18_shortened.MET")
#        self.hplc.slow_flowrate_ramp(r"D:\Data2q\sugar-optimizer\autostartup_analysis",
#                                     method_list=("autostartup_005_Sugar-c18_shortened.MET",
                                                  # "autostartup_01_Sugar-c18_shortened.MET",
                                                  # "autostartup_015_Sugar-c18_shortened.MET",
                                                  # "autostartup_02_Sugar-c18_shortened.MET",
                                                  # "autostartup_025_Sugar-c18_shortened.MET",
                                                  # "autostartup_03_Sugar-c18_shortened.MET",
                                                  # "autostartup_035_Sugar-c18_shortened.MET",
                                                  # "autostartup_04_Sugar-c18_shortened.MET",
                                                  # "autostartup_045_Sugar-c18_shortened.MET",
#                                                  "autostartup_05_Sugar-c18_shortened.MET",))
#        self.hplc.load_file(r"D:\Data2q\sugar-optimizer\autostartup_analysis\auto_Sugar-c18_shortened.MET")

        # Todo fill
        # commander.load_file("opendedicatedproject") # open a project for measurements

        # fill the activator to the hamilton syringe
        self.pumps['activator'].refill_syringe(4, 8)

        self.pumps['quencher'].set_maximum_pressure(5)


class Scheduler:
    """put together procedures and conditions, assign ID, put this to experiment Queue"""

    def __init__(self, graph: dict):

        self.graph = graph
        self.procedure = FlowProcedure(self.graph)
        self.experiment_queue = queue.Queue()
        # start worker
        self.experiment_worker = Thread(target=self.experiment_handler)
        self.experiment_worker.start()

        # create a worker function which compares these two. For efficiency, it will just check if analysed_samples is
        # empty. If not, it will get the respective experimental conditions from started_experiments. Combine the two
        # and drop it to the sql. in future, also hand it to the optimizer
        self.started_experiments = {}
        # later transfer to dict to hold analysis results, for now it only holds analysed sample
        self.analysed_samples = []

        self.data_worker = Thread(target=self.data_handler)
        self.data_worker.start()

        self._experiment_running = False

        # takes necessery steps to initialise the platform
        self.procedure.get_platform_ready()

    @property
    def experiment_running(self) -> bool:
        "returns the flag if experiment is running"
        return self._experiment_running

    @experiment_running.setter
    def experiment_running(self, experiment_running: bool):
        self._experiment_running = experiment_running

    def data_handler(self):
        """Checks if there is new analysis results. Since there may be multiple result files, these need to be pruned to individual ID and put into the set"""

        while True:
            for experiment_id, experiment_conditions in self.started_experiments:
                if not experiment_conditions.experiment_finished:
                    # needs to
                    for analysed_samples_files in self.analysed_samples:
                        if str(experiment_id) in analysed_samples_files:
                            experiment_conditions.experiment_finished = True
                            self.experiment_running = False
                            # TODO this can be expanded to trigger the analysis of the sample


    # just puts minimal conditions to the queue. Initially, this can be done manually/iterating over parameter space
    def create_experiment(self, conditions: ExperimentConditions) -> None:
        self.experiment_queue.put(conditions)

    def experiment_handler(self):
        """sits in separate thread, checks if previous job is finished and if so grabs new job from queue and executes it in a new thread"""
        while True:
            sleep(1)
            if self.experiment_queue.not_empty and not self.experiment_running:
                # get raw experimental data, derive actual platform parameters, create sequence function and execute that in a thread
                experiment: ExperimentConditions = self.experiment_queue.get()
                # append the experiment  to the dictionary
                individual_conditions = FlowConditions(experiment, self.graph)
                self.started_experiments[individual_conditions.experiment_id] = experiment
                new_thread = Thread(target=FlowProcedure.individual_procedure,
                                    args=(self.procedure, individual_conditions,))
                new_thread.start()
                self.experiment_running = True
                print(f'Experiment Running was set to {self.experiment_running} by experiment handler')
                # this should be called when experiment is over
                self.experiment_queue.task_done()
            elif self.experiment_queue.empty and not self.experiment_running:
                # start timer in separate thread. this timer should be killed by having sth in the queue again. When exceeding some time, platform shuts down
                pass


if __name__ == "__main__":
    # FlowGraph as dicitonary
    log = logging.getLogger()
    # missing init parameters
    SugarPlatform = {
        # try to combine two pumps to one. flow rate with ratio gives individual flow rate
        'pumps': {
            'donor': Elite11(PumpIO("COM11"), address=0, diameter=14.567, volume_syringe=10),

            'activator': ML600(HamiltonPumpIO("COM12"), 5),

            'quencher': KnauerPump("192.168.10.113"),
        },
        'HPLC': ClarityInterface(remote=True, host='192.168.10.11', port=10014, instrument_number=2),


        'chiller': Huber('COM1'),
        # assume always the same volume from pump to inlet, before T-mixer can be neglected, times three for inlets since 3 equal inlets
        'internal_volumes': {'dead_volume_before_reactor': (56+3)* 3 * flowchem_ureg.microliter, # TODO misses volume from tmixer to steel capillaries
                             'volume_mixing': 9.5 * flowchem_ureg.microliter,
                             'volume_reactor': 68.8 * flowchem_ureg.microliter,
                             'dead_volume_to_HPLC': (56+15) * flowchem_ureg.microliter,
                             }
    }

    #
    fr = FileReceiver('192.168.10.20', 10339, allowed_address='192.168.10.11')
    scheduler = Scheduler(SugarPlatform)

    # This obviously could be included into the scheduler
    results_listener = ResultListener('D:\\transferred_chromatograms', '*.txt', scheduler.analysed_samples)

    scheduler.create_experiment(ExperimentConditions(residence_time_in_seconds=1))
    scheduler.create_experiment(ExperimentConditions(temperature_in_celsius=23))
    scheduler.create_experiment(ExperimentConditions(residence_time_in_seconds=5))
    scheduler.create_experiment(ExperimentConditions(residence_time_in_seconds=10))
    scheduler.create_experiment(ExperimentConditions(residence_time_in_seconds=20))

    # TODO when queue empty, after some while everything should be switched off
