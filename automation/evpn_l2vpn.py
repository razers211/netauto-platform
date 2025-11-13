from .network_automation import NetworkAutomationError

class EVPNManager:
    """EVPN and L2VPN management for Juniper MX."""
    
    def __init__(self, device_manager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
    
    def create_evpn_instance(self, instance_name, vpls_id, rd=None, route_target=None, route_target_id=None, encapsulation='mpls', replication_type='ingress', description=None):
        if 'juniper' not in self.device_type:
            raise NetworkAutomationError(f"EVPN not supported on {self.device_type}")
        commands = [
            f'set routing-instances {instance_name} instance-type evpn-vpls',
            f'set routing-instances {instance_name} vlan-id {vpls_id}'
        ]
        if rd:
            commands.insert(2, f'set routing-instances {instance_name} route-distinguisher {rd}')
        if route_target and route_target_id:
            commands.extend([
                f'set routing-instances {instance_name} vrf-target target:{route_target}:{route_target_id}',
                f'set routing-instances {instance_name} vrf-target target:{route_target}:{route_target_id}'
            ])
        commands.extend([
            f'set routing-instances {instance_name} protocols evpn encapsulation {encapsulation}',
            f'set routing-instances {instance_name} protocols evpn default-gateway do-not-advertise',
            f'set routing-instances {instance_name} replication-type {replication_type}'
        ])
        if description:
            commands.append(f'set routing-instances {instance_name} description "{description}"')
        return self.device.execute_config_commands(commands)
    
    def add_bridge_domain_to_evpn(self, instance_name, bd_name, vlan_id, interface=None, description=None):
        if 'juniper' not in self.device_type:
            raise NetworkAutomationError(f"EVPN not supported on {self.device_type}")
        commands = [
            f'set routing-instances {instance_name} bridge-domains {bd_name} domain-type vlan',
            f'set routing-instances {instance_name} bridge-domains {bd_name} vlan-id {vlan_id}'
        ]
        if interface:
            commands.append(f'set routing-instances {instance_name} bridge-domains {bd_name} interface {interface}')
        if description:
            commands.append(f'set routing-instances {instance_name} bridge-domains {bd_name} description "{description}"')
        return self.device.execute_config_commands(commands)

    def create_l2vpws(self, service_name, local_if, remote_ip, vc_id, description=None):
        if 'juniper' not in self.device_type:
            raise NetworkAutomationError(f"L2VPWS not supported on {self.device_type}")
        commands = [
            f'set protocols l2circuit neighbor {remote_ip} interface {local_if} virtual-circuit-id {vc_id}'
        ]
        if description:
            commands.append(f'set protocols l2circuit neighbor {remote_ip} interface {local_if} virtual-circuit-id {vc_id} description "{description}"')
        return self.device.execute_config_commands(commands)

    def create_l2vpn_vpls(self, service_name, vpls_id, rd=None, rt_both=None, description=None):
        if 'juniper' not in self.device_type:
            raise NetworkAutomationError(f"VPLS not supported on {self.device_type}")
        commands = [
            f'set routing-instances {service_name} instance-type vpls',
            f'set routing-instances {service_name} vlan-id {vpls_id}'
        ]
        if rd:
            commands.insert(2, f'set routing-instances {service_name} route-distinguisher {rd}')
        if rt_both:
            commands.extend([
                f'set routing-instances {service_name} vrf-target target:{rt_both}',
                f'set routing-instances {service_name} vrf-target target:{rt_both}'
            ])
        if description:
            commands.append(f'set routing-instances {service_name} description "{description}"')
        return self.device.execute_config_commands(commands)

    def assign_interface_to_vpls(self, service_name, interface, vlan_id):
        if 'juniper' not in self.device_type:
            raise NetworkAutomationError(f"VPLS not supported on {self.device_type}")
        commands = [
            f'set routing-instances {service_name} interface {interface}',
            f'set interfaces {interface} unit 0 family bridge interface-mode trunk',
            f'set interfaces {interface} unit 0 family bridge vlan-id-list [ {vlan_id} ]'
        ]
        return self.device.execute_config_commands(commands)
