import math

 
class Trace:
    def __init__(self):
        self.env = None
        self.tx_pkt = list()
        self.success_tx_pkt = list()
        self.success_tx_bit = 0
        self.consume_energy = 0  # watt
        self.initial_energy = None
        self.reset_time = None

    def set_env(self, env):
        self.env = env
        self.reset_time = self.env.now

    def set_initial_energy(self, energy):
        self.initial_energy = energy

    def reset(self):
        self.tx_pkt.clear()
        self.success_tx_pkt.clear()
        self.success_tx_bit = 0
        self.consume_energy = 0
        self.reset_time = self.env.now

    def add_tx_pkt(self, packet):
        self.tx_pkt.append(packet)
        tx_power = packet.get_spectrum_tx_params().tx_power
        self.add_consumed_energy(tx_power)

    def add_success_tx_pkt(self, packet):
        self.success_tx_pkt.append(packet)
        self.success_tx_bit += packet.get_size() * 8

    def get_throughput(self):
        if self.env is None:
            print('simpy.env was not initialized')
            return -1
        return self.success_tx_bit / (self.env.now - self.reset_time)

    def get_delay(self):
        pass

    def add_consumed_energy(self, dbm):
        # convert dBm to watt
        if dbm == 0:
            w = 0.001
        else:
            mw = math.pow(10.0, dbm / 10.0)
            w = mw / 1000.0

        self.consume_energy += w

    def get_energy_consumption_ratio(self):
        if self.initial_energy is None:
            print('Initial energy was not initialized')
        else:
            return self.consume_energy / self.initial_energy

    def get_pkt_delivery_ratio(self):
        if len(self.success_tx_pkt) == 0:
            return 0

        return len(self.success_tx_pkt) / len(self.tx_pkt)
