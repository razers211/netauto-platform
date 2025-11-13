from junos.eznc import Device
from junos.eznc.utils.config import Config
from junos.eznc.exception import ConnectError, ConfigLoadError, CommitError

class JuniperPyEZDevice:
    def __init__(self, host, user, password, port=22, timeout=30):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.timeout = timeout
        self.dev = None

    def connect(self):
        try:
            self.dev = Device(host=self.host, user=self.user, password=self.password, port=self.port, timeout=self.timeout)
            self.dev.open()
            return True
        except Exception:
            return False

    def disconnect(self):
        if self.dev:
            try:
                self.dev.close()
            except:
                pass

    def load_set(self, commands):
        cfg = Config(self.dev)
        cfg.load('\n'.join(commands), format='set')
        return cfg.diff()

    def commit(self):
        cfg = Config(self.dev)
        return cfg.commit()

    def discard_changes(self):
        cfg = Config(self.dev)
        cfg.rollback()

    def get_config(self):
        return self.dev.rpc.get_config(filter_xml=None, options={'format': 'set'})

    def run_cli(self, cmd):
        return self.dev.cli(cmd, warning=False)

    def list_interfaces(self):
        output = self.run_cli('show interfaces terse | display xml')
        lines = output.split('\n')
        ifaces = []
        for line in lines:
            if '<interface-name>' in line:
                name = line.split('>')[1].split('<')[0]
                ifaces.append(name)
        return ifaces

    def list_ae(self):
        output = self.run_cli('show interfaces terse | display xml')
        ae = []
        lines = output.split('\n')
        for line in lines:
            if '<name>' in line and 'ae' in line:
                ae.append(line.split('>')[1].split('<')[0])
        return ae

    def list_vrfs(self):
        output = self.run_cli('show configuration routing-instances | display xml')
        lines = output.split('\n')
        vrfs = []
        in_instance = False
        for line in lines:
            if '<routing-instance>' in line:
                in_instance = True
                continue
            if in_instance and '<name>' in line:
                vrfs.append(line.split('>')[1].split('<')[0])
                in_instance = False
        return vrfs

class JuniperInterfaceManager:
    def __init__(self, device):
        self.device = device

    def configure_l3_unit(self, interface, unit, ip_address, prefix_length, description=None):
        commands = [f'set interfaces {interface} unit {unit} family inet address {ip_address}/{prefix_length}']
        if description:
            commands.append(f'set interfaces {interface} unit {unit} description "{description}"')
        return self.device.load_set(commands)

    def create_ae(self, ae_name, members=None, lacp=True):
        commands = [f'set interfaces {ae_name} aggregated-ether-options lacp active'] if lacp else [f'set interfaces {ae_name}']
        if members:
            for member in members:
                commands.append(f'set interfaces {member} ether-options gigabit-options redundant-parent {ae_name}')
        return self.device.load_set(commands)

    def add_ae_member(self, ae_name, member_interface):
        cmd = [f'set interfaces {member_interface} ether-options gigabit-options redundant-parent {ae_name}']
        return self.device.load_set(cmd)

    def configure_ae_unit(self, ae_name, unit, ip_address, prefix_length, description=None):
        commands = [f'set interfaces {ae_name} unit {unit} family inet address {ip_address}/{prefix_length}']
        if description:
            commands.append(f'set interfaces {ae_name} unit {unit} description "{description}"')
        return self.device.load_set(commands)

class JuniperVRFManager:
    def __init__(self, device):
        self.device = device

    def create_vrf(self, vrf_name, description=None):
        commands = [f'set routing-instances {vrf_name} instance-type virtual-router']
        if description:
            commands.append(f'set routing-instances {vrf_name} description "{description}"')
        return self.device.load_set(commands)

    def assign_interface_to_vrf(self, vrf_name, interface, unit, ip_address, prefix_length):
        commands = [
            f'set routing-instances {vrf_name} interface {interface}.{unit}',
            f'set interfaces {interface} unit {unit} family inet address {ip_address}/{prefix_length}'
        ]
        return self.device.load_set(commands)

    def add_static_route(self, vrf_name, network, prefix_length, next_hop):
        cmd = [f'set routing-instances {vrf_name} routing-options static route {network}/{prefix_length} next-hop {next_hop}']
        return self.device.load_set(cmd)

class JuniperRoutingManager:
    def __init__(self, device):
        self.device = device

    def add_static_route(self, network, prefix_length, next_hop, vrf_name=None):
        if vrf_name:
            cmd = [f'set routing-instances {vrf_name} routing-options static route {network}/{prefix_length} next-hop {next_hop}']
        else:
            cmd = [f'set routing-options static route {network}/{prefix_length} next-hop {next_hop}']
        return self.device.load_set(cmd)

    def configure_ospf(self, area_id, networks=None):
        commands = [f'set protocols ospf area 0.0.0.{area_id}']
        if networks:
            for net in networks:
                commands.append(f'set protocols ospf area 0.0.0.{area_id} interface {net["interface"]}')
        return self.device.load_set(commands)

    def configure_bgp(self, local_as, router_id, neighbors=None):
        commands = [
            f'set protocols bgp group internal type internal',
            f'set protocols bgp local-as {local_as}',
            f'set protocols bgp router-id {router_id}'
        ]
        if neighbors:
            for neighbor in neighbors:
                commands.append(f'set protocols bgp group internal neighbor {neighbor["ip"]} peer-as {neighbor["remote_as"]}')
        return self.device.load_set(commands)

    def configure_bgp_vrf(self, vrf_name, local_as, neighbors=None):
        commands = [
            f'set routing-instances {vrf_name} protocols bgp local-as {local_as}',
            f'set routing-instances {vrf_name} protocols bgp group internal type internal'
        ]
        if neighbors:
            for neighbor in neighbors:
                commands.append(f'set routing-instances {vrf_name} protocols bgp group internal neighbor {neighbor["ip"]} peer-as {neighbor["remote_as"]}')
        return self.device.load_set(commands)