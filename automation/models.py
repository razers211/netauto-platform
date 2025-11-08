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
        ('bgp_evpn', 'BGP EVPN'),
        ('evpn_instance', 'EVPN Instance'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=25, choices=TASK_TYPES)
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
    
    def __str__(self):
        return f"Result for {self.task}"
