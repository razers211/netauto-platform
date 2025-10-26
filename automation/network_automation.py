"""
Network automation scripts using Netmiko for Cisco and Huawei devices.
"""

import time
import logging
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from typing import Dict, List, Optional, Tuple
import re

logger = logging.getLogger(__name__)


class NetworkAutomationError(Exception):
    """Custom exception for network automation errors."""
    pass


class NetworkDeviceManager:
    """
    Manager class for network device operations using Netmiko.
    Supports both Cisco and Huawei devices.
    """
    
    def __init__(self, device_params: Dict):
        self.device_params = device_params
        self.connection = None
        
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        
    def connect(self) -> bool:
        """Establish connection to network device."""
        try:
            self.connection = ConnectHandler(**self.device_params)
            logger.info(f"Connected to {self.device_params['host']}")
            return True
        except NetmikoTimeoutException as e:
            logger.error(f"Timeout connecting to {self.device_params['host']}: {e}")
            raise NetworkAutomationError(f"Connection timeout: {e}")
        except NetmikoAuthenticationException as e:
            logger.error(f"Authentication failed for {self.device_params['host']}: {e}")
            raise NetworkAutomationError(f"Authentication failed: {e}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.device_params['host']}: {e}")
            raise NetworkAutomationError(f"Connection failed: {e}")
    
    def disconnect(self):
        """Close connection to network device."""
        if self.connection:
            self.connection.disconnect()
            logger.info(f"Disconnected from {self.device_params['host']}")
    
    def execute_command(self, command: str, use_textfsm: bool = False) -> str:
        """Execute a single command on the device."""
        if not self.connection:
            raise NetworkAutomationError("Not connected to device")
        
        logger.info(f"Executing command: {command}")
        try:
            if use_textfsm:
                output = self.connection.send_command(command, use_textfsm=True)
            else:
                output = self.connection.send_command(command)
            
            logger.info(f"Command output length: {len(output) if output else 0} characters")
            return output if output else "No output received from device"
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise NetworkAutomationError(f"Command failed: {e}")
    
    def execute_config_commands(self, commands: List[str]) -> str:
        """Execute configuration commands on the device."""
        if not self.connection:
            raise NetworkAutomationError("Not connected to device")
        
        device_type = self.device_params.get('device_type', '')
        
        try:
            # Enter configuration mode based on device type
            if 'cisco' in device_type:
                # Cisco devices: enter configure terminal mode
                self.connection.config_mode()
                output = self.connection.send_config_set(commands)
                self.connection.exit_config_mode()
                # Save configuration
                save_output = self.connection.save_config()
                return output + "\n" + save_output
                
            elif 'huawei' in device_type:
                # Huawei devices: enter system-view mode
                self.connection.send_command("system-view")
                
                # Send configuration commands
                config_output = ""
                for command in commands:
                    try:
                        cmd_output = self.connection.send_command(command)
                        config_output += f"{command}: {cmd_output}\n"
                    except Exception as e:
                        logger.warning(f"Command '{command}' failed: {e}")
                        config_output += f"{command}: ERROR - {e}\n"
                
                # Exit system-view
                self.connection.send_command("quit")
                
                # Commit configuration first (Huawei requirement)
                try:
                    commit_output = self.connection.send_command("commit")
                except Exception as e:
                    commit_output = f"Commit failed: {e}"
                
                # Save configuration
                try:
                    save_output = self.connection.send_command("save")
                    # Handle save confirmation
                    if "Y/N" in save_output or "y/n" in save_output or "overwrite" in save_output.lower():
                        save_output += "\n" + self.connection.send_command("y")
                except Exception as e:
                    save_output = f"Save failed: {e}"
                
                return config_output + f"\n\n--- COMMIT OUTPUT ---\n{commit_output}\n\n--- SAVE OUTPUT ---\n{save_output}"
                
            else:
                # Fallback to netmiko's default behavior
                output = self.connection.send_config_set(commands)
                save_output = self.connection.save_config()
                return output + "\n" + save_output
                
        except Exception as e:
            logger.error(f"Configuration failed: {e}")
            # Try to exit config mode if we're stuck
            try:
                if 'cisco' in device_type:
                    self.connection.exit_config_mode()
                elif 'huawei' in device_type:
                    self.connection.send_command("quit")
            except:
                pass
            raise NetworkAutomationError(f"Configuration failed: {e}")


class VLANManager:
    """VLAN management operations for network devices."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
    
    def create_vlan(self, vlan_id: int, vlan_name: str = None) -> str:
        """Create VLAN on the device."""
        if not (1 <= vlan_id <= 4094):
            raise NetworkAutomationError("VLAN ID must be between 1 and 4094")
        
        if 'cisco' in self.device_type:
            return self._create_cisco_vlan(vlan_id, vlan_name)
        elif 'huawei' in self.device_type:
            return self._create_huawei_vlan(vlan_id, vlan_name)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def _create_cisco_vlan(self, vlan_id: int, vlan_name: str = None) -> str:
        """Create VLAN on Cisco device."""
        commands = [f"vlan {vlan_id}"]
        if vlan_name:
            commands.append(f"name {vlan_name}")
        
        return self.device.execute_config_commands(commands)
    
    def _create_huawei_vlan(self, vlan_id: int, vlan_name: str = None) -> str:
        """Create VLAN on Huawei device."""
        commands = [f"vlan {vlan_id}"]
        if vlan_name:
            commands.append(f"description {vlan_name}")
        commands.append("quit")
        
        return self.device.execute_config_commands(commands)
    
    def delete_vlan(self, vlan_id: int) -> str:
        """Delete VLAN from the device."""
        if not (1 <= vlan_id <= 4094):
            raise NetworkAutomationError("VLAN ID must be between 1 and 4094")
        
        if 'cisco' in self.device_type:
            commands = [f"no vlan {vlan_id}"]
        elif 'huawei' in self.device_type:
            commands = [f"undo vlan {vlan_id}"]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def show_vlans(self) -> str:
        """Show VLAN configuration."""
        if 'cisco' in self.device_type:
            return self.device.execute_command("show vlan brief")
        elif 'huawei' in self.device_type:
            return self.device.execute_command("display vlan")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")


class InterfaceManager:
    """Interface configuration operations for network devices."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
    
    def configure_access_port(self, interface: str, vlan_id: int) -> str:
        """Configure interface as access port."""
        if 'cisco' in self.device_type:
            commands = [
                f"interface {interface}",
                "switchport mode access",
                f"switchport access vlan {vlan_id}",
                "no shutdown"
            ]
        elif 'huawei' in self.device_type:
            commands = [
                f"interface {interface}",
                "port link-type access",
                f"port default vlan {vlan_id}",
                "undo shutdown",
                "quit"
            ]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_trunk_port(self, interface: str, allowed_vlans: str = "all") -> str:
        """Configure interface as trunk port."""
        if 'cisco' in self.device_type:
            commands = [
                f"interface {interface}",
                "switchport mode trunk",
                "no shutdown"
            ]
            if allowed_vlans != "all":
                commands.insert(-1, f"switchport trunk allowed vlan {allowed_vlans}")
        elif 'huawei' in self.device_type:
            commands = [
                f"interface {interface}",
                "port link-type trunk",
                "undo shutdown",
                "quit"
            ]
            if allowed_vlans != "all":
                commands.insert(-2, f"port trunk allow-pass vlan {allowed_vlans}")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_ip_address(self, interface: str, ip_address: str, subnet_mask: str) -> str:
        """Configure IP address on interface."""
        if 'cisco' in self.device_type:
            commands = [
                f"interface {interface}",
                f"ip address {ip_address} {subnet_mask}",
                "no shutdown"
            ]
        elif 'huawei' in self.device_type:
            # Convert subnet mask to prefix length for Huawei
            prefix_length = self._mask_to_prefix(subnet_mask)
            commands = [
                f"interface {interface}",
                f"ip address {ip_address} {prefix_length}",
                "undo shutdown",
                "quit"
            ]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def _mask_to_prefix(self, mask: str) -> int:
        """Convert subnet mask to prefix length."""
        mask_parts = mask.split('.')
        binary = ''.join([bin(int(part))[2:].zfill(8) for part in mask_parts])
        return binary.count('1')
    
    def configure_vlan_interface(self, vlan_id: int, ip_address: str, subnet_mask: str, 
                               vrf_name: str = None, description: str = None, enable: bool = True) -> str:
        """Configure VLAN interface (SVI) with Layer 3 settings."""
        if 'cisco' in self.device_type:
            return self._cisco_vlan_interface(vlan_id, ip_address, subnet_mask, vrf_name, description, enable)
        elif 'huawei' in self.device_type:
            return self._huawei_vlan_interface(vlan_id, ip_address, subnet_mask, vrf_name, description, enable)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def _cisco_vlan_interface(self, vlan_id: int, ip_address: str, subnet_mask: str, 
                            vrf_name: str = None, description: str = None, enable: bool = True) -> str:
        """Configure VLAN interface on Cisco device."""
        commands = [f"interface vlan {vlan_id}"]
        
        if description:
            commands.append(f"description {description}")
        
        if vrf_name:
            commands.append(f"ip vrf forwarding {vrf_name}")
        
        commands.append(f"ip address {ip_address} {subnet_mask}")
        
        if enable:
            commands.append("no shutdown")
        else:
            commands.append("shutdown")
        
        return self.device.execute_config_commands(commands)
    
    def _huawei_vlan_interface(self, vlan_id: int, ip_address: str, subnet_mask: str, 
                             vrf_name: str = None, description: str = None, enable: bool = True) -> str:
        """Configure VLAN interface on Huawei device."""
        interface_name = f"Vlanif{vlan_id}"
        prefix_length = self._mask_to_prefix(subnet_mask)
        
        commands = [f"interface {interface_name}"]
        
        if description:
            commands.append(f"description {description}")
        
        if vrf_name:
            commands.append(f"ip binding vpn-instance {vrf_name}")
        
        commands.append(f"ip address {ip_address} {prefix_length}")
        
        if enable:
            commands.append("undo shutdown")
        else:
            commands.append("shutdown")
        
        commands.append("quit")
        
        return self.device.execute_config_commands(commands)
    
    def show_interfaces(self) -> str:
        """Show interface status."""
        if 'cisco' in self.device_type:
            return self.device.execute_command("show ip interface brief")
        elif 'huawei' in self.device_type:
            return self.device.execute_command("display interface brief")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")


class RoutingManager:
    """Routing configuration operations for network devices."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
    
    def add_static_route(self, network: str, mask: str, next_hop: str, vrf_name: str = None) -> str:
        """Add static route."""
        if 'cisco' in self.device_type:
            if vrf_name:
                commands = [f"ip route vrf {vrf_name} {network} {mask} {next_hop}"]
            else:
                commands = [f"ip route {network} {mask} {next_hop}"]
        elif 'huawei' in self.device_type:
            prefix_length = self._mask_to_prefix(mask)
            if vrf_name:
                commands = [f"ip route-static vpn-instance {vrf_name} {network} {prefix_length} {next_hop}"]
            else:
                commands = [f"ip route-static {network} {prefix_length} {next_hop}"]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def remove_static_route(self, network: str, mask: str, next_hop: str, vrf_name: str = None) -> str:
        """Remove static route."""
        if 'cisco' in self.device_type:
            if vrf_name:
                commands = [f"no ip route vrf {vrf_name} {network} {mask} {next_hop}"]
            else:
                commands = [f"no ip route {network} {mask} {next_hop}"]
        elif 'huawei' in self.device_type:
            prefix_length = self._mask_to_prefix(mask)
            if vrf_name:
                commands = [f"undo ip route-static vpn-instance {vrf_name} {network} {prefix_length} {next_hop}"]
            else:
                commands = [f"undo ip route-static {network} {prefix_length} {next_hop}"]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_ospf(self, process_id: int, router_id: str, networks: List[Dict], vrf_name: str = None) -> str:
        """Configure OSPF routing.
        
        networks format: [{'network': '192.168.1.0', 'wildcard': '0.0.0.255', 'area': '0'}]
        """
        if 'cisco' in self.device_type:
            if vrf_name:
                commands = [
                    f"router ospf {process_id} vrf {vrf_name}",
                    f"router-id {router_id}"
                ]
            else:
                commands = [
                    f"router ospf {process_id}",
                    f"router-id {router_id}"
                ]
            for net in networks:
                commands.append(f"network {net['network']} {net['wildcard']} area {net['area']}")
        elif 'huawei' in self.device_type:
            if vrf_name:
                commands = [
                    f"ospf {process_id} vpn-instance {vrf_name}",
                    f"router-id {router_id}"
                ]
            else:
                commands = [
                    f"ospf {process_id} router-id {router_id}"
                ]
            for net in networks:
                prefix_length = self._wildcard_to_prefix(net['wildcard'])
                commands.extend([
                    f"area {net['area']}",
                    f"network {net['network']} {prefix_length}",
                    "quit"
                ])
            commands.append("quit")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def _mask_to_prefix(self, mask: str) -> int:
        """Convert subnet mask to prefix length."""
        mask_parts = mask.split('.')
        binary = ''.join([bin(int(part))[2:].zfill(8) for part in mask_parts])
        return binary.count('1')
    
    def _wildcard_to_prefix(self, wildcard: str) -> int:
        """Convert wildcard mask to prefix length."""
        wildcard_parts = wildcard.split('.')
        # Convert wildcard to subnet mask
        mask_parts = [str(255 - int(part)) for part in wildcard_parts]
        mask = '.'.join(mask_parts)
        return self._mask_to_prefix(mask)
    
    def show_routes(self) -> str:
        """Show routing table."""
        if 'cisco' in self.device_type:
            return self.device.execute_command("show ip route")
        elif 'huawei' in self.device_type:
            return self.device.execute_command("display ip routing-table")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")


class DeviceInfoManager:
    """Device information and monitoring operations."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
    
    def get_version(self) -> str:
        """Get device version information."""
        if 'cisco' in self.device_type:
            return self.device.execute_command("show version")
        elif 'huawei' in self.device_type:
            return self.device.execute_command("display version")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def get_running_config(self) -> str:
        """Get running configuration."""
        if 'cisco' in self.device_type:
            return self.device.execute_command("show running-config")
        elif 'huawei' in self.device_type:
            return self.device.execute_command("display current-configuration")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def backup_config(self) -> str:
        """Backup device configuration."""
        return self.get_running_config()
    
    def get_system_info(self) -> Dict:
        """Get comprehensive system information."""
        info = {}
        try:
            info['version'] = self.get_version()
            info['interfaces'] = InterfaceManager(self.device).show_interfaces()
            info['vlans'] = VLANManager(self.device).show_vlans()
            info['routes'] = RoutingManager(self.device).show_routes()
        except Exception as e:
            logger.error(f"Error gathering system info: {e}")
            info['error'] = str(e)
        
        return info


class VRFManager:
    """VRF management operations for network devices."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
    
    def create_vrf(self, vrf_name: str, rd: str = None, description: str = None) -> str:
        """Create VRF on the device."""
        if 'cisco' in self.device_type:
            return self._create_cisco_vrf(vrf_name, rd, description)
        elif 'huawei' in self.device_type:
            return self._create_huawei_vrf(vrf_name, rd, description)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def _create_cisco_vrf(self, vrf_name: str, rd: str = None, description: str = None) -> str:
        """Create VRF on Cisco device."""
        commands = [f"ip vrf {vrf_name}"]
        if rd:
            commands.append(f"rd {rd}")
        if description:
            commands.append(f"description {description}")
        
        return self.device.execute_config_commands(commands)
    
    def _create_huawei_vrf(self, vrf_name: str, rd: str = None, description: str = None) -> str:
        """Create VRF on Huawei device."""
        commands = [f"ip vpn-instance {vrf_name}"]
        if rd:
            commands.append(f"route-distinguisher {rd}")
        if description:
            commands.append(f"description {description}")
        commands.append("quit")
        
        return self.device.execute_config_commands(commands)
    
    def delete_vrf(self, vrf_name: str) -> str:
        """Delete VRF from the device."""
        if 'cisco' in self.device_type:
            commands = [f"no ip vrf {vrf_name}"]
        elif 'huawei' in self.device_type:
            commands = [f"undo ip vpn-instance {vrf_name}"]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def assign_vrf_to_interface(self, interface: str, vrf_name: str, ip_address: str = None, subnet_mask: str = None) -> str:
        """Assign VRF to interface with optional IP configuration."""
        if 'cisco' in self.device_type:
            return self._cisco_vrf_interface(interface, vrf_name, ip_address, subnet_mask)
        elif 'huawei' in self.device_type:
            return self._huawei_vrf_interface(interface, vrf_name, ip_address, subnet_mask)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def _cisco_vrf_interface(self, interface: str, vrf_name: str, ip_address: str = None, subnet_mask: str = None) -> str:
        """Assign VRF to Cisco interface."""
        commands = [
            f"interface {interface}",
            f"ip vrf forwarding {vrf_name}"
        ]
        
        if ip_address and subnet_mask:
            commands.append(f"ip address {ip_address} {subnet_mask}")
        
        commands.append("no shutdown")
        
        return self.device.execute_config_commands(commands)
    
    def _huawei_vrf_interface(self, interface: str, vrf_name: str, ip_address: str = None, subnet_mask: str = None) -> str:
        """Assign VRF to Huawei interface."""
        commands = [
            f"interface {interface}",
            f"ip binding vpn-instance {vrf_name}"
        ]
        
        if ip_address and subnet_mask:
            # Convert subnet mask to prefix length for Huawei
            prefix_length = self._mask_to_prefix(subnet_mask)
            commands.append(f"ip address {ip_address} {prefix_length}")
        
        commands.extend(["undo shutdown", "quit"])
        
        return self.device.execute_config_commands(commands)
    
    def _mask_to_prefix(self, mask: str) -> int:
        """Convert subnet mask to prefix length."""
        mask_parts = mask.split('.')
        binary = ''.join([bin(int(part))[2:].zfill(8) for part in mask_parts])
        return binary.count('1')
    
    def show_vrfs(self) -> str:
        """Show VRF configuration."""
        if 'cisco' in self.device_type:
            return self.device.execute_command("show ip vrf")
        elif 'huawei' in self.device_type:
            return self.device.execute_command("display ip vpn-instance")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")


class BGPManager:
    """BGP configuration operations for network devices."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
    
    def configure_bgp_neighbor(self, as_number: int, neighbor_ip: str, remote_as: int, 
                              vrf_name: str = None, description: str = None) -> str:
        """Configure BGP neighbor."""
        if 'cisco' in self.device_type:
            return self._cisco_bgp_neighbor(as_number, neighbor_ip, remote_as, vrf_name, description)
        elif 'huawei' in self.device_type:
            return self._huawei_bgp_neighbor(as_number, neighbor_ip, remote_as, vrf_name, description)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def _cisco_bgp_neighbor(self, as_number: int, neighbor_ip: str, remote_as: int, 
                           vrf_name: str = None, description: str = None) -> str:
        """Configure BGP neighbor on Cisco device."""
        if vrf_name:
            commands = [
                f"router bgp {as_number}",
                f"address-family ipv4 vrf {vrf_name}",
                f"neighbor {neighbor_ip} remote-as {remote_as}",
                f"neighbor {neighbor_ip} activate"
            ]
            if description:
                commands.insert(-1, f"neighbor {neighbor_ip} description {description}")
            commands.append("exit-address-family")
        else:
            commands = [
                f"router bgp {as_number}",
                f"neighbor {neighbor_ip} remote-as {remote_as}"
            ]
            if description:
                commands.append(f"neighbor {neighbor_ip} description {description}")
        
        return self.device.execute_config_commands(commands)
    
    def _huawei_bgp_neighbor(self, as_number: int, neighbor_ip: str, remote_as: int, 
                            vrf_name: str = None, description: str = None) -> str:
        """Configure BGP neighbor on Huawei device."""
        if vrf_name:
            commands = [
                f"bgp {as_number}",
                f"ipv4-family vpn-instance {vrf_name}",
                f"peer {neighbor_ip} as-number {remote_as}"
            ]
            if description:
                commands.append(f"peer {neighbor_ip} description {description}")
            commands.extend(["quit", "quit"])
        else:
            commands = [
                f"bgp {as_number}",
                f"peer {neighbor_ip} as-number {remote_as}"
            ]
            if description:
                commands.append(f"peer {neighbor_ip} description {description}")
            commands.append("quit")
        
        return self.device.execute_config_commands(commands)
    
    def advertise_network(self, as_number: int, network: str, mask: str, vrf_name: str = None) -> str:
        """Advertise network in BGP."""
        if 'cisco' in self.device_type:
            return self._cisco_bgp_network(as_number, network, mask, vrf_name)
        elif 'huawei' in self.device_type:
            return self._huawei_bgp_network(as_number, network, mask, vrf_name)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def _cisco_bgp_network(self, as_number: int, network: str, mask: str, vrf_name: str = None) -> str:
        """Advertise network in Cisco BGP."""
        if vrf_name:
            commands = [
                f"router bgp {as_number}",
                f"address-family ipv4 vrf {vrf_name}",
                f"network {network} mask {mask}",
                "exit-address-family"
            ]
        else:
            commands = [
                f"router bgp {as_number}",
                f"network {network} mask {mask}"
            ]
        
        return self.device.execute_config_commands(commands)
    
    def _huawei_bgp_network(self, as_number: int, network: str, mask: str, vrf_name: str = None) -> str:
        """Advertise network in Huawei BGP."""
        prefix_length = self._mask_to_prefix(mask)
        
        if vrf_name:
            commands = [
                f"bgp {as_number}",
                f"ipv4-family vpn-instance {vrf_name}",
                f"network {network} {prefix_length}",
                "quit",
                "quit"
            ]
        else:
            commands = [
                f"bgp {as_number}",
                f"network {network} {prefix_length}",
                "quit"
            ]
        
        return self.device.execute_config_commands(commands)
    
    def _mask_to_prefix(self, mask: str) -> int:
        """Convert subnet mask to prefix length."""
        mask_parts = mask.split('.')
        binary = ''.join([bin(int(part))[2:].zfill(8) for part in mask_parts])
        return binary.count('1')
    
    def configure_bgp_vrf(self, as_number: int, vrf_name: str, router_id: str = None, 
                         import_rt: str = None, export_rt: str = None) -> str:
        """Configure BGP for VRF with route targets."""
        if 'cisco' in self.device_type:
            return self._cisco_bgp_vrf(as_number, vrf_name, router_id, import_rt, export_rt)
        elif 'huawei' in self.device_type:
            return self._huawei_bgp_vrf(as_number, vrf_name, router_id, import_rt, export_rt)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def _cisco_bgp_vrf(self, as_number: int, vrf_name: str, router_id: str = None, 
                      import_rt: str = None, export_rt: str = None) -> str:
        """Configure BGP for VRF on Cisco device."""
        commands = [
            f"router bgp {as_number}",
            f"address-family ipv4 vrf {vrf_name}"
        ]
        
        if router_id:
            commands.insert(1, f"bgp router-id {router_id}")
        
        # Configure VRF definition with route targets
        vrf_commands = [f"ip vrf {vrf_name}"]
        if import_rt:
            vrf_commands.append(f"route-target import {import_rt}")
        if export_rt:
            vrf_commands.append(f"route-target export {export_rt}")
        
        commands = vrf_commands + commands + ["exit-address-family"]
        
        return self.device.execute_config_commands(commands)
    
    def _huawei_bgp_vrf(self, as_number: int, vrf_name: str, router_id: str = None, 
                       import_rt: str = None, export_rt: str = None) -> str:
        """Configure BGP for VRF on Huawei device."""
        # Configure VPN instance with route targets
        vrf_commands = [f"ip vpn-instance {vrf_name}"]
        if import_rt:
            vrf_commands.append(f"route-target import {import_rt}")
        if export_rt:
            vrf_commands.append(f"route-target export {export_rt}")
        vrf_commands.append("quit")
        
        # Configure BGP
        bgp_commands = [f"bgp {as_number}"]
        if router_id:
            bgp_commands.append(f"router-id {router_id}")
        bgp_commands.extend([
            f"ipv4-family vpn-instance {vrf_name}",
            "quit",
            "quit"
        ])
        
        commands = vrf_commands + bgp_commands
        
        return self.device.execute_config_commands(commands)
    
    def configure_bgp_route_reflector(self, as_number: int, router_id: str, clients: list = None) -> str:
        """Configure BGP Route Reflector."""
        if 'cisco' in self.device_type:
            commands = [
                f"router bgp {as_number}",
                f"bgp router-id {router_id}",
                "bgp cluster-id 1"
            ]
            if clients:
                for client in clients:
                    commands.append(f"neighbor {client} route-reflector-client")
        elif 'huawei' in self.device_type:
            commands = [
                f"bgp {as_number}",
                f"router-id {router_id}",
                "reflector cluster-id 1"
            ]
            if clients:
                for client in clients:
                    commands.append(f"peer {client} reflect-client")
            commands.append("quit")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_bgp_confederation(self, as_number: int, confed_id: int, confed_peers: list = None) -> str:
        """Configure BGP Confederation."""
        if 'cisco' in self.device_type:
            commands = [
                f"router bgp {as_number}",
                f"bgp confederation identifier {confed_id}"
            ]
            if confed_peers:
                peers_str = ' '.join(map(str, confed_peers))
                commands.append(f"bgp confederation peers {peers_str}")
        elif 'huawei' in self.device_type:
            commands = [
                f"bgp {as_number}",
                f"confederation id {confed_id}"
            ]
            if confed_peers:
                for peer in confed_peers:
                    commands.append(f"confederation peer-as {peer}")
            commands.append("quit")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_bgp_community(self, as_number: int, community_list: str, action: str = 'permit') -> str:
        """Configure BGP Community lists."""
        if 'cisco' in self.device_type:
            commands = [
                f"ip community-list standard {community_list} {action} {community_list}",
                f"router bgp {as_number}",
                "bgp community new-format"
            ]
        elif 'huawei' in self.device_type:
            commands = [
                f"ip community-filter {community_list} {action} {community_list}",
                f"bgp {as_number}",
                "quit"
            ]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_bgp_route_map(self, as_number: int, route_map: str, neighbor_ip: str, direction: str = 'in') -> str:
        """Apply route-map to BGP neighbor."""
        if 'cisco' in self.device_type:
            commands = [
                f"router bgp {as_number}",
                f"neighbor {neighbor_ip} route-map {route_map} {direction}"
            ]
        elif 'huawei' in self.device_type:
            commands = [
                f"bgp {as_number}",
                f"peer {neighbor_ip} route-policy {route_map} {direction}",
                "quit"
            ]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_bgp_multipath(self, as_number: int, paths: int = 4) -> str:
        """Configure BGP multipath."""
        if 'cisco' in self.device_type:
            commands = [
                f"router bgp {as_number}",
                f"maximum-paths {paths}",
                f"maximum-paths ibgp {paths}"
            ]
        elif 'huawei' in self.device_type:
            commands = [
                f"bgp {as_number}",
                f"maximum load-balancing {paths}",
                "quit"
            ]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_bgp_route_reflector(self, as_number: int, router_id: str, cluster_id: int = 1, clients: list = None) -> str:
        """Configure BGP Route Reflector."""
        if 'cisco' in self.device_type:
            commands = [
                f"router bgp {as_number}",
                f"bgp router-id {router_id}",
                f"bgp cluster-id {cluster_id}"
            ]
            if clients:
                for client in clients:
                    commands.append(f"neighbor {client} route-reflector-client")
        elif 'huawei' in self.device_type:
            commands = [
                f"bgp {as_number}",
                f"router-id {router_id}",
                f"reflector cluster-id {cluster_id}"
            ]
            if clients:
                for client in clients:
                    commands.append(f"peer {client} reflect-client")
            commands.append("quit")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_bgp_confederation(self, as_number: int, confed_id: int, confed_peers: list = None) -> str:
        """Configure BGP Confederation."""
        if 'cisco' in self.device_type:
            commands = [
                f"router bgp {as_number}",
                f"bgp confederation identifier {confed_id}"
            ]
            if confed_peers:
                peers_str = ' '.join(map(str, confed_peers))
                commands.append(f"bgp confederation peers {peers_str}")
        elif 'huawei' in self.device_type:
            commands = [
                f"bgp {as_number}",
                f"confederation id {confed_id}"
            ]
            if confed_peers:
                for peer in confed_peers:
                    commands.append(f"confederation peer-as {peer}")
            commands.append("quit")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_bgp_multipath(self, as_number: int, ebgp_paths: int = 4, ibgp_paths: int = 4) -> str:
        """Configure BGP multipath load balancing."""
        if 'cisco' in self.device_type:
            commands = [
                f"router bgp {as_number}",
                f"maximum-paths {ebgp_paths}",
                f"maximum-paths ibgp {ibgp_paths}"
            ]
        elif 'huawei' in self.device_type:
            commands = [
                f"bgp {as_number}",
                f"maximum load-balancing {max(ebgp_paths, ibgp_paths)}",
                "quit"
            ]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def show_bgp_summary(self, vrf_name: str = None) -> str:
        """Show BGP summary."""
        if 'cisco' in self.device_type:
            if vrf_name:
                return self.device.execute_command(f"show ip bgp vpnv4 vrf {vrf_name} summary")
            else:
                return self.device.execute_command("show ip bgp summary")
        elif 'huawei' in self.device_type:
            if vrf_name:
                return self.device.execute_command(f"display bgp vpnv4 vpn-instance {vrf_name} peer")
            else:
                return self.device.execute_command("display bgp peer")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")


class AdvancedOSPFManager:
    """Advanced OSPF configuration operations for network devices."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
    
    def configure_ospf_area(self, process_id: int, area_id: str, area_type: str = 'standard', 
                           stub_default_cost: int = None, nssa_default: bool = False) -> str:
        """Configure OSPF area with different types."""
        if 'cisco' in self.device_type:
            commands = [f"router ospf {process_id}"]
            
            if area_type == 'stub':
                commands.append(f"area {area_id} stub")
                if stub_default_cost:
                    commands.append(f"area {area_id} default-cost {stub_default_cost}")
            elif area_type == 'totally_stub':
                commands.append(f"area {area_id} stub no-summary")
            elif area_type == 'nssa':
                cmd = f"area {area_id} nssa"
                if nssa_default:
                    cmd += " default-information-originate"
                commands.append(cmd)
            elif area_type == 'totally_nssa':
                commands.append(f"area {area_id} nssa no-summary")
                
        elif 'huawei' in self.device_type:
            commands = [f"ospf {process_id}"]
            
            if area_type == 'stub':
                commands.extend([
                    f"area {area_id}",
                    "stub",
                    "quit"
                ])
                if stub_default_cost:
                    commands.insert(-1, f"default-cost {stub_default_cost}")
            elif area_type == 'totally_stub':
                commands.extend([
                    f"area {area_id}",
                    "stub no-summary",
                    "quit"
                ])
            elif area_type == 'nssa':
                commands.extend([
                    f"area {area_id}",
                    "nssa",
                    "quit"
                ])
            elif area_type == 'totally_nssa':
                commands.extend([
                    f"area {area_id}",
                    "nssa no-summary",
                    "quit"
                ])
            commands.append("quit")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_ospf_authentication(self, process_id: int, area_id: str = None, 
                                    interface: str = None, auth_type: str = 'md5', 
                                    key_id: int = 1, password: str = 'cisco123') -> str:
        """Configure OSPF authentication."""
        if 'cisco' in self.device_type:
            commands = []
            if interface:
                # Interface-level authentication
                commands.extend([
                    f"interface {interface}",
                    f"ip ospf message-digest-key {key_id} md5 {password}" if auth_type == 'md5' else f"ip ospf authentication-key {password}"
                ])
            else:
                # Area-level authentication
                commands.extend([
                    f"router ospf {process_id}",
                    f"area {area_id} authentication {'message-digest' if auth_type == 'md5' else ''}"
                ])
                
        elif 'huawei' in self.device_type:
            commands = []
            if interface:
                commands.extend([
                    f"interface {interface}",
                    f"ospf authentication-mode {'md5' if auth_type == 'md5' else 'simple'} {key_id if auth_type == 'md5' else ''} {password}",
                    "quit"
                ])
            else:
                commands.extend([
                    f"ospf {process_id}",
                    f"area {area_id}",
                    f"authentication-mode {'md5' if auth_type == 'md5' else 'simple'}",
                    "quit",
                    "quit"
                ])
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_ospf_summarization(self, process_id: int, area_id: str, network: str, 
                                   mask: str, cost: int = None, not_advertise: bool = False) -> str:
        """Configure OSPF area range summarization."""
        if 'cisco' in self.device_type:
            cmd = f"area {area_id} range {network} {mask}"
            if not_advertise:
                cmd += " not-advertise"
            elif cost:
                cmd += f" cost {cost}"
            commands = [f"router ospf {process_id}", cmd]
            
        elif 'huawei' in self.device_type:
            commands = [
                f"ospf {process_id}",
                f"area {area_id}"
            ]
            prefix_length = self._mask_to_prefix(mask)
            cmd = f"abr-summary {network} {prefix_length}"
            if not_advertise:
                cmd += " not-advertise"
            elif cost:
                cmd += f" cost {cost}"
            commands.extend([cmd, "quit", "quit"])
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def configure_ospf_virtual_link(self, process_id: int, area_id: str, neighbor_id: str, 
                                  hello_interval: int = 10, dead_interval: int = 40) -> str:
        """Configure OSPF virtual link."""
        if 'cisco' in self.device_type:
            commands = [
                f"router ospf {process_id}",
                f"area {area_id} virtual-link {neighbor_id} hello-interval {hello_interval} dead-interval {dead_interval}"
            ]
        elif 'huawei' in self.device_type:
            commands = [
                f"ospf {process_id}",
                f"area {area_id}",
                f"vlink-peer {neighbor_id}",
                f"hello {hello_interval}",
                f"dead {dead_interval}",
                "quit",
                "quit"
            ]
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def _mask_to_prefix(self, mask: str) -> int:
        """Convert subnet mask to prefix length."""
        mask_parts = mask.split('.')
        binary = ''.join([bin(int(part))[2:].zfill(8) for part in mask_parts])
        return binary.count('1')


class EVPNManager:
    """EVPN configuration operations for Huawei devices."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
        
        if 'huawei' not in self.device_type:
            raise NetworkAutomationError("EVPN configuration is only supported on Huawei devices")
    
    def configure_evpn_instance(self, evpn_instance: str, route_distinguisher: str, 
                              export_rt: str, import_rt: str) -> str:
        """Configure EVPN instance."""
        commands = [
            f"evpn vpn-instance {evpn_instance} bd-mode",
            f"route-distinguisher {route_distinguisher}",
            f"vpn-target {export_rt} export-extcommunity",
            f"vpn-target {import_rt} import-extcommunity",
            "quit"
        ]
        
        return self.device.execute_config_commands(commands)
    
    def configure_bgp_evpn(self, as_number: int, neighbor_ip: str, source_interface: str = None) -> str:
        """Configure BGP EVPN address family."""
        commands = [
            f"bgp {as_number}",
            f"peer {neighbor_ip} as-number {as_number}"
        ]
        
        if source_interface:
            commands.append(f"peer {neighbor_ip} connect-interface {source_interface}")
        
        commands.extend([
            "ipv4-family unicast",
            f"undo peer {neighbor_ip} enable",
            "quit",
            "l2vpn-family evpn",
            f"peer {neighbor_ip} enable",
            f"peer {neighbor_ip} advertise-community",
            "quit",
            "quit"
        ])
        
        return self.device.execute_config_commands(commands)
    
    def configure_vbdif_interface(self, vbdif_id: int, ip_address: str, mask: str, 
                                 bridge_domain: int) -> str:
        """Configure VBDIF interface for EVPN."""
        prefix_length = self._mask_to_prefix(mask)
        
        commands = [
            f"interface Vbdif{vbdif_id}",
            f"ip address {ip_address} {prefix_length}",
            f"ip binding vpn-instance {bridge_domain}",
            "undo shutdown",
            "quit"
        ]
        
        return self.device.execute_config_commands(commands)
    
    def configure_bridge_domain(self, bd_id: int, evpn_instance: str = None) -> str:
        """Configure Bridge Domain for EVPN."""
        commands = [f"bridge-domain {bd_id}"]
        
        if evpn_instance:
            commands.append(f"evpn binding vpn-instance {evpn_instance}")
        
        commands.extend([
            "quit"
        ])
        
        return self.device.execute_config_commands(commands)
    
    def configure_evpn_ethernet_segment(self, interface: str, esi: str, df_election: str = 'mod') -> str:
        """Configure EVPN Ethernet Segment Identifier."""
        commands = [
            f"interface {interface}",
            f"evpn multi-homing identifier {esi}",
            f"evpn multi-homing mode {df_election}",
            "quit"
        ]
        
        return self.device.execute_config_commands(commands)
    
    def _mask_to_prefix(self, mask: str) -> int:
        """Convert subnet mask to prefix length."""
        mask_parts = mask.split('.')
        binary = ''.join([bin(int(part))[2:].zfill(8) for part in mask_parts])
        return binary.count('1')


class VXLANManager:
    """VXLAN configuration operations for Huawei devices."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
        
        if 'huawei' not in self.device_type:
            raise NetworkAutomationError("VXLAN configuration is only supported on Huawei devices")
    
    def configure_vxlan_tunnel(self, tunnel_id: int, source_ip: str, destination_ip: str, 
                             vni: int) -> str:
        """Configure VXLAN tunnel interface."""
        commands = [
            f"interface Tunnel{tunnel_id}",
            "tunnel-protocol vxlan",
            f"source {source_ip}",
            f"destination {destination_ip}",
            f"vxlan vni {vni}",
            "undo shutdown",
            "quit"
        ]
        
        return self.device.execute_config_commands(commands)
    
    def configure_nve_interface(self, nve_id: int, source_ip: str, vni_mapping: dict = None) -> str:
        """Configure NVE (Network Virtualization Edge) interface."""
        commands = [
            f"interface Nve{nve_id}",
            f"source {source_ip}",
        ]
        
        if vni_mapping:
            for vni, bd_id in vni_mapping.items():
                commands.append(f"vni {vni} l2-vni {bd_id}")
        
        commands.extend([
            "undo shutdown",
            "quit"
        ])
        
        return self.device.execute_config_commands(commands)
    
    def configure_vxlan_bd_binding(self, bd_id: int, vni: int, nve_interface: int) -> str:
        """Bind Bridge Domain to VNI."""
        commands = [
            f"bridge-domain {bd_id}",
            f"vxlan vni {vni}",
            f"vxlan binding nve {nve_interface}",
            "quit"
        ]
        
        return self.device.execute_config_commands(commands)
    
    def configure_vxlan_access_port(self, interface: str, bd_id: int) -> str:
        """Configure interface as VXLAN access port."""
        commands = [
            f"interface {interface}",
            "portswitch",
            f"bridge-domain {bd_id}",
            "undo shutdown",
            "quit"
        ]
        
        return self.device.execute_config_commands(commands)
    
    def configure_vxlan_gateway(self, bd_id: int, gateway_ip: str, mask: str, 
                              vbdif_id: int = None) -> str:
        """Configure VXLAN gateway."""
        if not vbdif_id:
            vbdif_id = bd_id
        
        prefix_length = self._mask_to_prefix(mask)
        
        # Configure bridge domain with gateway
        bd_commands = [
            f"bridge-domain {bd_id}",
            f"arp broadcast-suppress enable",
            "quit"
        ]
        
        # Configure VBDIF interface
        vbdif_commands = [
            f"interface Vbdif{vbdif_id}",
            f"ip address {gateway_ip} {prefix_length}",
            f"bridge-domain {bd_id}",
            "undo shutdown",
            "quit"
        ]
        
        return (self.device.execute_config_commands(bd_commands) + "\n" + 
                self.device.execute_config_commands(vbdif_commands))
    
    def _mask_to_prefix(self, mask: str) -> int:
        """Convert subnet mask to prefix length."""
        mask_parts = mask.split('.')
        binary = ''.join([bin(int(part))[2:].zfill(8) for part in mask_parts])
        return binary.count('1')


class DataCenterFabricManager:
    """Comprehensive DataCenter Fabric automation for Huawei EVPN VXLAN spine-leaf architecture."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
        
        if 'huawei' not in self.device_type:
            raise NetworkAutomationError("DataCenter Fabric configuration is only supported on Huawei devices")
    
    def configure_spine_underlay(self, router_id: str, as_number: int, spine_interfaces: list,
                                spine_ip_range: str = "10.0.0.0/30") -> str:
        """Configure spine switch underlay (BGP + OSPF)."""
        commands = [
            # Configure OSPF for underlay
            "ospf 1",
            f"router-id {router_id}",
            "area 0",
            "quit",
            "quit",
            
            # Configure BGP for EVPN
            f"bgp {as_number}",
            f"router-id {router_id}",
            "peer spine-leaf-evpn internal",
            "peer spine-leaf-evpn connect-interface LoopBack0",
            
            # Enable EVPN address family
            "ipv4-family unicast",
            "undo peer spine-leaf-evpn enable",
            "quit",
            "l2vpn-family evpn",
            "peer spine-leaf-evpn enable",
            "peer spine-leaf-evpn reflect-client",
            "quit",
            "quit"
        ]
        
        # Configure spine interfaces
        for idx, interface in enumerate(spine_interfaces):
            base_ip = self._calculate_spine_ip(spine_ip_range, idx)
            commands.extend([
                f"interface {interface}",
                f"ip address {base_ip} 30",
                "ospf enable area 0",
                "undo shutdown",
                "quit"
            ])
        
        # Configure loopback
        commands.extend([
            "interface LoopBack0",
            f"ip address {router_id} 32",
            "ospf enable area 0",
            "quit"
        ])
        
        return self.device.execute_config_commands(commands)
    
    def configure_leaf_underlay(self, router_id: str, as_number: int, spine_interfaces: list,
                               leaf_id: int, spine_ip_range: str = "10.0.0.0/30") -> str:
        """Configure leaf switch underlay (BGP + OSPF)."""
        commands = [
            # Configure OSPF for underlay
            "ospf 1",
            f"router-id {router_id}",
            "area 0",
            "quit",
            "quit",
            
            # Configure BGP for EVPN
            f"bgp {as_number}",
            f"router-id {router_id}",
            
            # Configure loopback
            "interface LoopBack0",
            f"ip address {router_id} 32",
            "ospf enable area 0",
            "quit"
        ]
        
        # Configure leaf uplink interfaces to spines
        for idx, interface in enumerate(spine_interfaces):
            peer_ip = self._calculate_leaf_ip(spine_ip_range, leaf_id, idx)
            commands.extend([
                f"interface {interface}",
                f"ip address {peer_ip} 30",
                "ospf enable area 0",
                "undo shutdown",
                "quit"
            ])
        
        # Add spine peers to BGP
        spine_loopbacks = self._get_spine_loopbacks(spine_interfaces)
        for spine_ip in spine_loopbacks:
            commands.extend([
                f"bgp {as_number}",
                f"peer {spine_ip} as-number {as_number}",
                f"peer {spine_ip} connect-interface LoopBack0",
                "ipv4-family unicast",
                f"undo peer {spine_ip} enable",
                "quit",
                "l2vpn-family evpn",
                f"peer {spine_ip} enable",
                "quit",
                "quit"
            ])
        
        return self.device.execute_config_commands(commands)
    
    def deploy_tenant_network(self, tenant_name: str, vni: int, vlan_id: int, 
                            gateway_ip: str, subnet_mask: str, 
                            access_interfaces: list = None, 
                            route_target: str = None) -> str:
        """Deploy a complete tenant network with EVPN VXLAN."""
        if not route_target:
            route_target = f"65000:{vni}"
        
        prefix_length = self._mask_to_prefix(subnet_mask)
        
        commands = [
            # Create EVPN instance
            f"evpn vpn-instance {tenant_name} bd-mode",
            f"route-distinguisher auto",
            f"vpn-target {route_target} export-extcommunity",
            f"vpn-target {route_target} import-extcommunity",
            "quit",
            
            # Create bridge domain
            f"bridge-domain {vlan_id}",
            f"evpn binding vpn-instance {tenant_name}",
            "quit",
            
            # Create VLAN
            f"vlan {vlan_id}",
            f"description {tenant_name}_VLAN",
            "quit",
            
            # Configure NVE interface (assuming NVE1 exists)
            "interface Nve1",
            f"vni {vni} l2-vni {vlan_id}",
            "quit",
            
            # Create VBDIF for gateway
            f"interface Vbdif{vlan_id}",
            f"ip address {gateway_ip} {prefix_length}",
            f"bridge-domain {vlan_id}",
            "arp broadcast-suppress enable",
            "undo shutdown",
            "quit"
        ]
        
        # Configure access interfaces if provided
        if access_interfaces:
            for interface in access_interfaces:
                commands.extend([
                    f"interface {interface}",
                    "portswitch",
                    "port link-type access",
                    f"port default vlan {vlan_id}",
                    "undo shutdown",
                    "quit"
                ])
        
        return self.device.execute_config_commands(commands)
    
    def configure_external_connectivity(self, border_leaf_config: dict) -> str:
        """Configure external connectivity for tenant networks (DCI/WAN)."""
        commands = []
        
        # Configure VRF for external connectivity
        vrf_name = border_leaf_config.get('vrf_name', 'EXTERNAL_VRF')
        rd = border_leaf_config.get('rd', 'auto')
        rt = border_leaf_config.get('rt', '65000:999')
        
        commands.extend([
            f"ip vpn-instance {vrf_name}",
            f"route-distinguisher {rd}",
            f"vpn-target {rt} export-extcommunity",
            f"vpn-target {rt} import-extcommunity",
            "quit"
        ])
        
        # Configure external interface
        ext_interface = border_leaf_config.get('external_interface')
        ext_ip = border_leaf_config.get('external_ip')
        ext_mask = border_leaf_config.get('external_mask')
        
        if ext_interface and ext_ip and ext_mask:
            prefix_length = self._mask_to_prefix(ext_mask)
            commands.extend([
                f"interface {ext_interface}",
                f"ip binding vpn-instance {vrf_name}",
                f"ip address {ext_ip} {prefix_length}",
                "undo shutdown",
                "quit"
            ])
        
        # Configure BGP for external advertisement
        as_number = border_leaf_config.get('as_number', 65000)
        external_peer = border_leaf_config.get('external_peer')
        external_as = border_leaf_config.get('external_as')
        
        if external_peer and external_as:
            commands.extend([
                f"bgp {as_number}",
                f"ipv4-family vpn-instance {vrf_name}",
                f"peer {external_peer} as-number {external_as}",
                "quit",
                "quit"
            ])
        
        return self.device.execute_config_commands(commands)
    
    def configure_multi_tenant_routing(self, tenant_networks: list, 
                                     external_vrf: str = 'EXTERNAL_VRF') -> str:
        """Configure routing between tenant networks and external connectivity."""
        commands = []
        
        for tenant in tenant_networks:
            tenant_name = tenant.get('name')
            tenant_vrf = tenant.get('vrf', tenant_name)
            advertise_external = tenant.get('advertise_external', False)
            
            if advertise_external:
                # Import/export route targets for external connectivity
                commands.extend([
                    f"evpn vpn-instance {tenant_name} bd-mode",
                    f"vpn-target 65000:999 import-extcommunity",  # Import from external
                    "quit"
                ])
                
                # Configure route leaking if needed
                tenant_networks_to_advertise = tenant.get('networks', [])
                for network in tenant_networks_to_advertise:
                    commands.extend([
                        f"ip vpn-instance {external_vrf}",
                        f"import route-target {tenant.get('rt', f'65000:{tenant.get("vni", 10000)}')} policy TENANT_TO_EXTERNAL",
                        "quit"
                    ])
        
        return self.device.execute_config_commands(commands)
    
    def deploy_full_fabric_configuration(self, fabric_config: dict) -> str:
        """Deploy complete datacenter fabric with all tenant networks."""
        device_role = fabric_config.get('device_role')  # 'spine' or 'leaf'
        device_id = fabric_config.get('device_id', 1)
        as_number = fabric_config.get('as_number', 65000)
        
        if device_role == 'spine':
            router_id = fabric_config.get('spine_loopback', f"10.255.255.{device_id}")
            spine_interfaces = fabric_config.get('spine_interfaces', [])
            return self.configure_spine_underlay(router_id, as_number, spine_interfaces)
        
        elif device_role == 'leaf':
            router_id = fabric_config.get('leaf_loopback', f"10.255.254.{device_id}")
            spine_interfaces = fabric_config.get('uplink_interfaces', [])
            
            # Configure underlay
            result = self.configure_leaf_underlay(router_id, as_number, spine_interfaces, device_id)
            
            # Configure NVE interface
            nve_config = fabric_config.get('nve_config', {})
            if nve_config:
                nve_commands = [
                    "interface Nve1",
                    f"source {router_id}",
                    "undo shutdown",
                    "quit"
                ]
                result += "\n" + self.device.execute_config_commands(nve_commands)
            
            # Deploy tenant networks
            tenant_networks = fabric_config.get('tenant_networks', [])
            for tenant in tenant_networks:
                tenant_result = self.deploy_tenant_network(
                    tenant['name'],
                    tenant['vni'],
                    tenant['vlan_id'],
                    tenant['gateway_ip'],
                    tenant['subnet_mask'],
                    tenant.get('access_interfaces', [])
                )
                result += "\n" + tenant_result
            
            # Configure external connectivity if this is a border leaf
            if fabric_config.get('is_border_leaf', False):
                external_config = fabric_config.get('external_config', {})
                if external_config:
                    external_result = self.configure_external_connectivity(external_config)
                    result += "\n" + external_result
            
            return result
        
        else:
            raise NetworkAutomationError(f"Unknown device role: {device_role}")
    
    def _calculate_spine_ip(self, ip_range: str, interface_idx: int) -> str:
        """Calculate spine interface IP address."""
        # Simple IP calculation - in production, use proper IP addressing library
        base_ip = ip_range.split('/')[0]
        octets = base_ip.split('.')
        octets[3] = str(int(octets[3]) + (interface_idx * 4) + 1)
        return '.'.join(octets)
    
    def _calculate_leaf_ip(self, ip_range: str, leaf_id: int, interface_idx: int) -> str:
        """Calculate leaf interface IP address."""
        base_ip = ip_range.split('/')[0]
        octets = base_ip.split('.')
        octets[3] = str(int(octets[3]) + (interface_idx * 4) + 1 + leaf_id)
        return '.'.join(octets)
    
    def _get_spine_loopbacks(self, spine_interfaces: list) -> list:
        """Get spine loopback addresses for BGP peering."""
        # Return predefined spine loopbacks - in production, this would be dynamic
        return [f"10.255.255.{i+1}" for i in range(len(spine_interfaces))]
    
    def _mask_to_prefix(self, mask: str) -> int:
        """Convert subnet mask to prefix length."""
        mask_parts = mask.split('.')
        binary = ''.join([bin(int(part))[2:].zfill(8) for part in mask_parts])
        return binary.count('1')



def execute_network_task(device_params: Dict, task_type: str, parameters: Dict) -> Tuple[bool, str, str]:
    """
    Execute a network automation task.
    
    Returns:
        Tuple of (success: bool, result: str, error_message: str)
    """
    start_time = time.time()
    
    try:
        with NetworkDeviceManager(device_params) as device:
            if task_type == 'vlan_create':
                manager = VLANManager(device)
                result = manager.create_vlan(
                    parameters['vlan_id'], 
                    parameters.get('vlan_name')
                )
            
            elif task_type == 'vlan_delete':
                manager = VLANManager(device)
                result = manager.delete_vlan(parameters['vlan_id'])
            
            elif task_type == 'interface_config':
                manager = InterfaceManager(device)
                if parameters['mode'] == 'access':
                    result = manager.configure_access_port(
                        parameters['interface'], 
                        parameters['vlan_id']
                    )
                elif parameters['mode'] == 'trunk':
                    result = manager.configure_trunk_port(
                        parameters['interface'], 
                        parameters.get('allowed_vlans', 'all')
                    )
                elif parameters['mode'] == 'ip':
                    result = manager.configure_ip_address(
                        parameters['interface'],
                        parameters['ip_address'],
                        parameters['subnet_mask']
                    )
                else:
                    raise NetworkAutomationError(f"Unknown interface mode: {parameters['mode']}")
            
            elif task_type == 'vlan_interface_config':
                manager = InterfaceManager(device)
                result = manager.configure_vlan_interface(
                    parameters['vlan_id'],
                    parameters['ip_address'],
                    parameters['subnet_mask'],
                    parameters.get('vrf_name'),
                    parameters.get('description'),
                    parameters.get('enable_interface', True)
                )
            
            elif task_type == 'routing_static':
                manager = RoutingManager(device)
                if parameters.get('action') == 'remove':
                    result = manager.remove_static_route(
                        parameters['network'],
                        parameters['mask'],
                        parameters['next_hop'],
                        parameters.get('vrf_name')
                    )
                else:
                    result = manager.add_static_route(
                        parameters['network'],
                        parameters['mask'],
                        parameters['next_hop'],
                        parameters.get('vrf_name')
                    )
            
            elif task_type == 'routing_ospf':
                manager = RoutingManager(device)
                result = manager.configure_ospf(
                    parameters['process_id'],
                    parameters['router_id'],
                    parameters['networks'],
                    parameters.get('vrf_name')
                )
            
            elif task_type == 'show_version':
                manager = DeviceInfoManager(device)
                result = manager.get_version()
            
            elif task_type == 'show_interfaces':
                manager = InterfaceManager(device)
                result = manager.show_interfaces()
            
            elif task_type == 'show_vlan':
                manager = VLANManager(device)
                result = manager.show_vlans()
            
            elif task_type == 'show_routes':
                manager = RoutingManager(device)
                result = manager.show_routes()
            
            elif task_type == 'backup_config':
                manager = DeviceInfoManager(device)
                result = manager.backup_config()
            
            # VRF tasks
            elif task_type == 'vrf_create':
                manager = VRFManager(device)
                result = manager.create_vrf(
                    parameters['vrf_name'],
                    parameters.get('rd'),
                    parameters.get('description')
                )
            
            elif task_type == 'vrf_assign_interface':
                manager = VRFManager(device)
                result = manager.assign_vrf_to_interface(
                    parameters['interface'],
                    parameters['vrf_name'],
                    parameters.get('ip_address'),
                    parameters.get('subnet_mask')
                )
            
            # BGP tasks
            elif task_type == 'bgp_neighbor':
                manager = BGPManager(device)
                result = manager.configure_bgp_neighbor(
                    parameters['as_number'],
                    parameters['neighbor_ip'],
                    parameters['remote_as'],
                    parameters.get('vrf_name'),
                    parameters.get('description')
                )
            
            elif task_type == 'bgp_network':
                manager = BGPManager(device)
                result = manager.advertise_network(
                    parameters['as_number'],
                    parameters['network'],
                    parameters['mask'],
                    parameters.get('vrf_name')
                )
            
            elif task_type == 'bgp_vrf_config':
                manager = BGPManager(device)
                result = manager.configure_bgp_vrf(
                    parameters['as_number'],
                    parameters['vrf_name'],
                    parameters.get('router_id'),
                    parameters.get('import_rt'),
                    parameters.get('export_rt')
                )
            
            else:
                raise NetworkAutomationError(f"Unknown task type: {task_type}")
        
        execution_time = time.time() - start_time
        logger.info(f"Task {task_type} completed successfully in {execution_time:.2f}s")
        return True, result, ""
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = str(e)
        logger.error(f"Task {task_type} failed after {execution_time:.2f}s: {error_msg}")
        return False, "", error_msg
