from .juniper_pyez import JuniperPyEZDevice, JuniperInterfaceManager, JuniperVRFManager, JuniperRoutingManager

class JuniperDeviceManager:
    def __init__(self, device_params):
        self.device_params = device_params
        self.connection = None
        self.device_type = device_params.get('device_type', '')
        self.juniper_dev = JuniperPyEZDevice(
            host=device_params['host'],
            user=device_params['username'],
            password=device_params['password'],
            port=device_params.get('port', 22)
        )
        self.if_manager = None
        self.vrf_manager = None
        self.routing_manager = None

    def _ensure_connected(self):
        if not self.juniper_dev.dev:
            if not self.juniper_dev.connect():
                raise Exception('Connection failed')

    def __enter__(self):
        self.connect()
        self.if_manager = JuniperInterfaceManager(self.juniper_dev)
        self.vrf_manager = JuniperVRFManager(self.juniper_dev)
        self.routing_manager = JuniperRoutingManager(self.juniper_dev)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        return self.juniper_dev.connect()

    def disconnect(self):
        self.juniper_dev.disconnect()

    def execute_command(self, command):
        self._ensure_connected()
        return self.juniper_dev.run_cli(command)

    def execute_config_commands(self, commands):
        self._ensure_connected()
        diff = self.juniper_dev.load_set(commands)
        commit_result = self.juniper_dev.commit()
        return f'Diff:\n{diff}\n\nCommit:\n{commit_result}'

    def list_interfaces(self):
        self._ensure_connected()
        return self.juniper_dev.list_interfaces()

    def list_ae(self):
        self._ensure_connected()
        return self.juniper_dev.list_ae()

    def list_vrfs(self):
        self._ensure_connected()
        return self.juniper_dev.list_vrfs()