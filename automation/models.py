from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class Device(models.Model):
    DEVICE_TYPES = [
        ('cisco_ios', 'Cisco IOS'),
        ('cisco_xe', 'Cisco IOS-XE'),
        ('cisco_nxos', 'Cisco NX-OS'),
        ('huawei', 'Huawei VRP'),
        ('huawei_vrpv8', 'Huawei VRP v8'),
        ('juniper_mx', 'Juniper MX'),
        ('juniper_srx', 'Juniper SRX'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    host = models.GenericIPAddressField()
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=100)  # In production, encrypt this
    port = models.IntegerField(default=22)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_connected = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.host})"
    
    def get_connection_params(self):
        return {
            'device_type': self.device_type,
            'host': self.host,
            'username': self.username,
            'password': self.password,
            'port': self.port,
            'timeout': 30,
        }


class NetworkTask(models.Model):
    TASK_TYPES = [
        ('vlan_create', 'Create VLAN'),
        ('vlan_delete', 'Delete VLAN'),
        ('vlan_interface_config', 'Configure VLAN Interface'),
        ('interface_config', 'Configure Interface'),
        ('routing_static', 'Static Route'),
        ('routing_ospf', 'OSPF Configuration'),
        ('vrf_create', 'Create VRF'),
        ('vrf_delete', 'Delete VRF'),
        ('vrf_interface', 'Assign VRF to Interface'),
        ('bgp_neighbor', 'Configure BGP Neighbor'),
        ('bgp_network', 'Advertise BGP Network'),
        ('bgp_vrf', 'Configure BGP for VRF'),
        ('bgp_route_reflector', 'Configure BGP Route Reflector'),
        ('bgp_confederation', 'Configure BGP Confederation'),
        ('bgp_multipath', 'Configure BGP Multipath'),
        ('ospf_area', 'Configure OSPF Area'),
        ('ospf_authentication', 'Configure OSPF Authentication'),
        ('evpn_instance', 'Configure EVPN Instance'),
        ('bgp_evpn', 'Configure BGP EVPN'),
        ('vxlan_tunnel', 'Configure VXLAN Tunnel'),
        ('nve_interface', 'Configure NVE Interface'),
        ('vxlan_gateway', 'Configure VXLAN Gateway'),
        ('vxlan_access_port', 'Configure VXLAN Access Port'),
        ('show_version', 'Show Version'),
        ('show_interfaces', 'Show Interfaces'),
        ('show_vlan', 'Show VLANs'),
        ('show_routes', 'Show Routes'),
        ('show_vrf', 'Show VRFs'),
        ('show_bgp', 'Show BGP Summary'),
        ('backup_config', 'Backup Configuration'),
        ('ae_config', 'Configure AE Interface'),
        ('l2vpws', 'L2VPWS Instance'),
        ('l2vpn_vpls', 'L2VPN VPLS Instance'),
        ('bridge_domain', 'Bridge Domain Configuration'),
        ('huawei_eth_trunk', 'Huawei Eth-Trunk (M-LAG)'),
        ('interface_ipv6', 'Configure Interface IPv6'),
        ('vlan_interface_ipv6', 'Configure VLAN Interface IPv6'),
        ('routing_static_v6', 'Static Route IPv6'),
        ('bgp_neighbor_v6', 'Configure BGP Neighbor (IPv6)'),
        ('bgp_network_v6', 'Advertise BGP Network (IPv6)'),
        ('routing_ospf_v6', 'OSPFv3 (IPv6) Configuration'),
        ('datacenter_fabric', 'Deploy Full Fabric'),
        ('datacenter_fabric_single', 'Deploy Single Switch to Fabric'),
        ('multi_tenant_deployment', 'Multi-Tenant Deployment'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=30, choices=TASK_TYPES)
    parameters = models.JSONField(default=dict)  # Task-specific parameters
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_task_type_display()} on {self.device.name}"
    
    def duration(self):
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


class TaskResult(models.Model):
    task = models.OneToOneField(NetworkTask, on_delete=models.CASCADE)
    output = models.TextField()
    success = models.BooleanField(default=True)
    execution_time = models.FloatField()  # seconds
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Result for {self.task}"


class FabricDeployment(models.Model):
    """Track datacenter fabric deployments and their member switches."""
    FABRIC_STATUS = [
        ('building', 'Building'),
        ('active', 'Active'),
        ('updating', 'Updating'),
        ('decommissioned', 'Decommissioned'),
    ]
    
    fabric_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=FABRIC_STATUS, default='building')
    underlay_ip_range = models.CharField(max_length=50, default='10.0.0.0/30')
    as_number = models.IntegerField(default=65000)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # JSON fields for fabric topology
    spine_devices = models.JSONField(default=list, help_text="List of spine device IDs and configs")
    leaf_devices = models.JSONField(default=list, help_text="List of leaf device IDs and configs")
    border_leaf_devices = models.JSONField(default=list, help_text="List of border leaf device IDs and configs")
    tenant_networks = models.JSONField(default=list, help_text="Tenant networks deployed in this fabric")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Fabric: {self.fabric_name} ({self.get_status_display()})"
    
    def get_all_devices(self):
        """Get all device IDs in this fabric."""
        all_devices = []
        all_devices.extend([d['device_id'] for d in self.spine_devices])
        all_devices.extend([d['device_id'] for d in self.leaf_devices])
        all_devices.extend([d['device_id'] for d in self.border_leaf_devices])
        return list(set(all_devices))
    
    def get_device_role(self, device_id):
        """Get the role of a device in this fabric."""
        for device in self.spine_devices:
            if device['device_id'] == device_id:
                return 'spine'
        for device in self.leaf_devices:
            if device['device_id'] == device_id:
                return 'leaf'
        for device in self.border_leaf_devices:
            if device['device_id'] == device_id:
                return 'border_leaf'
        return None
