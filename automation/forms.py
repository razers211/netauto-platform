from django import forms
from .models import Device, NetworkTask
import json


class DeviceForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), help_text="Device login password")
    
    class Meta:
        model = Device
        fields = ['name', 'host', 'device_type', 'username', 'password', 'port', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'host': forms.TextInput(attrs={'placeholder': '192.168.1.1'}),
            'username': forms.TextInput(attrs={'placeholder': 'admin'}),
            'port': forms.NumberInput(attrs={'min': 1, 'max': 65535, 'value': 22}),
        }


class VLANCreateForm(forms.Form):
    vlan_id = forms.IntegerField(
        min_value=1, 
        max_value=4094, 
        label="VLAN ID",
        widget=forms.NumberInput(attrs={'placeholder': '100'})
    )
    vlan_name = forms.CharField(
        max_length=50, 
        required=False, 
        label="VLAN Name",
        widget=forms.TextInput(attrs={'placeholder': 'Sales_VLAN'})
    )


class VLANDeleteForm(forms.Form):
    vlan_id = forms.IntegerField(
        min_value=1, 
        max_value=4094, 
        label="VLAN ID",
        widget=forms.NumberInput(attrs={'placeholder': '100'})
    )


class InterfaceConfigForm(forms.Form):
    MODE_CHOICES = [
        ('access', 'Access Port'),
        ('trunk', 'Trunk Port'),
        ('ip', 'IP Address'),
    ]
    
    interface = forms.ChoiceField(
        choices=[],
        label="Interface",
        widget=forms.Select(attrs={'class': 'form-control interface-select'}),
        help_text='Select an interface from the device'
    )
    mode = forms.ChoiceField(choices=MODE_CHOICES, label="Configuration Mode")
    
    # Access port fields
    vlan_id = forms.IntegerField(
        min_value=1, 
        max_value=4094, 
        required=False, 
        label="VLAN ID",
        widget=forms.NumberInput(attrs={'placeholder': '100'})
    )
    
    # Trunk port fields
    allowed_vlans = forms.CharField(
        max_length=100, 
        required=False, 
        label="Allowed VLANs",
        widget=forms.TextInput(attrs={'placeholder': '1-10,20,30-40 or leave empty for all'})
    )
    
    # IP address fields
    ip_address = forms.GenericIPAddressField(
        required=False, 
        label="IP Address",
        widget=forms.TextInput(attrs={'placeholder': '192.168.1.1'})
    )
    subnet_mask = forms.CharField(
        max_length=15, 
        required=False, 
        label="Subnet Mask",
        widget=forms.TextInput(attrs={'placeholder': '255.255.255.0'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode')
        
        if mode == 'access' and not cleaned_data.get('vlan_id'):
            raise forms.ValidationError("VLAN ID is required for access port configuration.")
        
        if mode == 'ip':
            if not cleaned_data.get('ip_address'):
                raise forms.ValidationError("IP address is required for IP configuration.")
            if not cleaned_data.get('subnet_mask'):
                raise forms.ValidationError("Subnet mask is required for IP configuration.")
        
        return cleaned_data

class InterfaceIPv6Form(forms.Form):
    interface = forms.ChoiceField(
        choices=[],
        label="Interface",
        widget=forms.Select(attrs={'class': 'form-control interface-select'}),
        help_text='Select an interface from the device'
    )
    ipv6_address = forms.CharField(
        max_length=64,
        label='IPv6 Address',
        widget=forms.TextInput(attrs={'placeholder': '2001:db8::1'})
    )
    prefix_length = forms.IntegerField(
        min_value=1,
        max_value=128,
        label='Prefix Length',
        initial=64
    )

class VLANInterfaceIPv6Form(forms.Form):
    vlan_id = forms.IntegerField(min_value=1, max_value=4094, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}), label='VLAN ID')
    ipv6_address = forms.CharField(max_length=64, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2001:db8::1'}), label='IPv6 Address')
    prefix_length = forms.IntegerField(min_value=1, max_value=128, initial=64, widget=forms.NumberInput(attrs={'class': 'form-control'}), label='Prefix Length')
    vrf_name = forms.ChoiceField(choices=[('', 'Global (no VRF)')], required=False, widget=forms.Select(attrs={'class': 'form-control vrf-select'}), label='VRF Name')
    description = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}), label='Description (optional)')
    enable_interface = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), label='Enable interface')

class StaticRouteV6Form(forms.Form):
    ACTION_CHOICES = [('add', 'Add Route'), ('remove', 'Remove Route')]
    action = forms.ChoiceField(choices=ACTION_CHOICES, label='Action')
    prefix = forms.CharField(max_length=64, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2001:db8:1::/64'}), label='IPv6 Prefix')
    next_hop = forms.CharField(max_length=64, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2001:db8::2'}), label='Next Hop')
    vrf_name = forms.ChoiceField(choices=[('', 'Global (no VRF)')], required=False, widget=forms.Select(attrs={'class': 'form-control vrf-select'}), label='VRF Name')


class StaticRouteForm(forms.Form):
    ACTION_CHOICES = [
        ('add', 'Add Route'),
        ('remove', 'Remove Route'),
    ]
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, label="Action")
    network = forms.CharField(
        max_length=15, 
        label="Network",
        widget=forms.TextInput(attrs={'placeholder': '192.168.2.0'})
    )
    mask = forms.CharField(
        max_length=15, 
        label="Subnet Mask",
        widget=forms.TextInput(attrs={'placeholder': '255.255.255.0'})
    )
    next_hop = forms.GenericIPAddressField(
        label="Next Hop",
        widget=forms.TextInput(attrs={'placeholder': '192.168.1.1'})
    )
    vrf_name = forms.ChoiceField(
        choices=[('', 'Global (no VRF)')],
        required=False,
        label="VRF Name",
        widget=forms.Select(attrs={'class': 'form-control vrf-select'}),
        help_text='Optional VRF for VRF-aware routing (leave empty for global)'
    )


class OSPFConfigForm(forms.Form):
    process_id = forms.IntegerField(
        min_value=1, 
        max_value=65535, 
        label="Process ID",
        widget=forms.NumberInput(attrs={'placeholder': '1'})
    )
    router_id = forms.GenericIPAddressField(
        label="Router ID",
        widget=forms.TextInput(attrs={'placeholder': '1.1.1.1'})
    )
    vrf_name = forms.ChoiceField(
        choices=[('', 'Global (no VRF)')],
        required=False,
        label="VRF Name",
        widget=forms.Select(attrs={'class': 'form-control vrf-select'}),
        help_text='Optional VRF for VRF-aware OSPF (leave empty for global)'
    )
    networks = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4, 
            'placeholder': 'Enter networks in JSON format:\n[{"network": "192.168.1.0", "wildcard": "0.0.0.255", "area": "0"}]'
        }),
        label="Networks (JSON format)"
    )
    
    def clean_networks(self):
        networks_data = self.cleaned_data['networks']
        try:
            networks = json.loads(networks_data)
            if not isinstance(networks, list):
                raise forms.ValidationError("Networks must be a JSON array.")
            
            for network in networks:
                required_fields = ['network', 'wildcard', 'area']
                if not all(field in network for field in required_fields):
                    raise forms.ValidationError(
                        "Each network must have 'network', 'wildcard', and 'area' fields."
                    )
            
            return networks
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format.")

class OSPFv3ConfigForm(forms.Form):
    process_id = forms.IntegerField(min_value=1, max_value=65535, label='Process ID', widget=forms.NumberInput(attrs={'placeholder': '1'}))
    router_id = forms.GenericIPAddressField(label='Router ID', widget=forms.TextInput(attrs={'placeholder': '1.1.1.1'}))
    interfaces = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Interfaces JSON (e.g.)\n[{"interface": "GigabitEthernet0/0", "area": "0"}]'
        }),
        label='Interfaces (JSON)'
    )
    
    def clean_interfaces(self):
        data = self.cleaned_data['interfaces']
        try:
            items = json.loads(data)
            if not isinstance(items, list):
                raise forms.ValidationError('Interfaces must be a JSON array')
            for it in items:
                if not all(k in it for k in ['interface', 'area']):
                    raise forms.ValidationError("Each item must have 'interface' and 'area'")
            return items
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format')


class TaskExecutionForm(forms.Form):
    device = forms.ModelChoiceField(
        queryset=Device.objects.filter(is_active=True),
        empty_label="Select a device"
    )
    task_type = forms.ChoiceField(choices=[], label="Task Type")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['task_type'].choices = NetworkTask.TASK_TYPES


class DeviceTestForm(forms.Form):
    """Form to test device connectivity"""
    device = forms.ModelChoiceField(
        queryset=Device.objects.filter(is_active=True),
        empty_label="Select a device",
        label="Device to Test"
    )


class DeviceSelectionForm(forms.Form):
    """Simple form for device selection (used by show commands)"""
    device = forms.ModelChoiceField(
        queryset=Device.objects.filter(is_active=True),
        empty_label="Select a device",
        label="Target Device"
    )


class ShowRoutesForm(forms.Form):
    """Form for showing routing table with optional VRF support"""
    device = forms.ModelChoiceField(
        queryset=Device.objects.filter(is_active=True),
        empty_label="Select a device",
        label="Target Device"
    )
    vrf_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Leave empty for global routing table'}),
        help_text='Optional: Enter VRF name to show VRF-specific routing table'
    )


class VRFCreateForm(forms.Form):
    vrf_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CUSTOMER_A'}),
        help_text='Name of the VRF to create'
    )
    rd = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65000:1'}),
        help_text='Route Distinguisher (e.g., 65000:1)'
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Customer A VPN'}),
        help_text='Optional description for the VRF'
    )
    import_rt = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65000:1'}),
        help_text='Import Route Target (e.g., 65000:1)'
    )
    export_rt = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65000:1'}),
        help_text='Export Route Target (e.g., 65000:1)'
    )


class VRFAssignInterfaceForm(forms.Form):
    vrf_name = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control vrf-select'}),
        help_text='Select a VRF from the device'
    )
    interface = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control interface-select'}),
        help_text='Select an interface from the device'
    )
    ip_address = forms.GenericIPAddressField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '192.168.1.1'}),
        help_text='IP address for the interface (optional)'
    )
    subnet_mask = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '255.255.255.0'}),
        help_text='Subnet mask (e.g., 255.255.255.0)'
    )


class BGPNeighborForm(forms.Form):
    as_number = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65001'}),
        help_text='Local AS number'
    )
    neighbor_ip = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '192.168.1.2'}),
        help_text='Neighbor IP address'
    )
    remote_as = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65002'}),
        help_text='Remote AS number'
    )
    vrf_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CUSTOMER_A'}),
        help_text='VRF name (optional, for VRF-aware BGP)'
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Customer A BGP peer'}),
        help_text='Optional description for the neighbor'
    )


class BGPNetworkForm(forms.Form):
    as_number = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65001'}),
        help_text='Local AS number'
    )
    network = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '192.168.100.0'}),
        help_text='Network address to advertise'
    )
    mask = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '255.255.255.0'}),
        help_text='Subnet mask (e.g., 255.255.255.0)'
    )
    vrf_name = forms.ChoiceField(
        choices=[('', 'Global (no VRF)')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control vrf-select'}),
        help_text='VRF name (optional, for VRF-aware BGP)'
    )


class BGPVRFConfigForm(forms.Form):
    as_number = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65001'}),
        help_text='Local AS number'
    )
    vrf_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CUSTOMER_A'}),
        help_text='VRF name'
    )
    router_id = forms.GenericIPAddressField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1.1.1.1'}),
        help_text='BGP Router ID (optional)'
    )
    import_rt = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65000:1'}),
        help_text='Import Route Target (e.g., 65000:1)'
    )
    export_rt = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65000:1'}),
        help_text='Export Route Target (e.g., 65000:1)'
    )


class VLANInterfaceConfigForm(forms.Form):
    vlan_id = forms.IntegerField(
        min_value=1,
        max_value=4094,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}),
        help_text='VLAN ID for the interface (1-4094)'
    )
    ip_address = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '192.168.100.1'}),
        help_text='IP address for the VLAN interface'
    )
    subnet_mask = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '255.255.255.0'}),
        help_text='Subnet mask (e.g., 255.255.255.0)'
    )
    vrf_name = forms.ChoiceField(
        choices=[('', 'Global (no VRF)')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control vrf-select'}),
        help_text='Optional VRF to assign the interface to'
    )
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Gateway for VLAN 100'}),
        help_text='Optional description for the interface'
    )
    enable_interface = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Enable the interface after configuration'
    )


class BGPRouteReflectorForm(forms.Form):
    as_number = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65001'}),
        help_text='Local AS number'
    )
    router_id = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1.1.1.1'}),
        help_text='BGP Router ID'
    )
    cluster_id = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        help_text='Route Reflector cluster ID'
    )
    clients = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '192.168.1.2\n192.168.1.3'}),
        help_text='Route Reflector clients (one IP per line)'
    )


class BGPConfederationForm(forms.Form):
    as_number = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65001'}),
        help_text='Local AS number'
    )
    confederation_id = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65000'}),
        help_text='BGP Confederation identifier'
    )
    confederation_peers = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '65002\n65003'}),
        help_text='Confederation peer AS numbers (one per line)'
    )


class BGPMultipathForm(forms.Form):
    as_number = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65001'}),
        help_text='Local AS number'
    )
    ebgp_paths = forms.IntegerField(
        min_value=1,
        max_value=32,
        initial=4,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '4'}),
        help_text='Maximum EBGP paths for load balancing'
    )
    ibgp_paths = forms.IntegerField(
        min_value=1,
        max_value=32,
        initial=4,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '4'}),
        help_text='Maximum IBGP paths for load balancing'
    )


class OSPFAreaForm(forms.Form):
    AREA_TYPE_CHOICES = [
        ('standard', 'Standard Area'),
        ('stub', 'Stub Area'),
        ('totally_stub', 'Totally Stubby Area'),
        ('nssa', 'Not-So-Stubby Area (NSSA)'),
        ('totally_nssa', 'Totally NSSA')
    ]
    
    process_id = forms.IntegerField(
        min_value=1,
        max_value=65535,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        help_text='OSPF process ID'
    )
    area_id = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0 or 0.0.0.0'}),
        help_text='OSPF area ID (number or IP format)'
    )
    area_type = forms.ChoiceField(
        choices=AREA_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Type of OSPF area'
    )
    stub_default_cost = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=16777215,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        help_text='Default cost for stub area (optional)'
    )
    nssa_default_route = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Generate default route in NSSA'
    )


class OSPFAuthenticationForm(forms.Form):
    AUTH_TYPE_CHOICES = [
        ('simple', 'Simple Password'),
        ('md5', 'MD5 Authentication')
    ]
    
    process_id = forms.IntegerField(
        min_value=1,
        max_value=65535,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        help_text='OSPF process ID'
    )
    area_id = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0'}),
        help_text='Area ID for area-level auth (leave empty for interface-level)'
    )
    interface = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control interface-select'}),
        help_text='Interface for interface-level auth (leave empty for area-level)'
    )
    auth_type = forms.ChoiceField(
        choices=AUTH_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Authentication type'
    )
    key_id = forms.IntegerField(
        min_value=1,
        max_value=255,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        help_text='Key ID for MD5 authentication'
    )
    password = forms.CharField(
        max_length=50,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Authentication password'
    )


class EVPNInstanceForm(forms.Form):
    evpn_instance = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EVPN_INSTANCE_1'}),
        help_text='EVPN instance name'
    )
    route_distinguisher = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65001:1'}),
        help_text='Route Distinguisher (ASN:value or IP:value)'
    )
    export_rt = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65001:1'}),
        help_text='Export Route Target'
    )
    import_rt = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65001:1'}),
        help_text='Import Route Target'
    )


class BGPEVPNForm(forms.Form):
    as_number = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65001'}),
        help_text='Local AS number'
    )
    neighbor_ip = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '192.168.1.2'}),
        help_text='BGP EVPN neighbor IP address'
    )
    source_interface = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control interface-select'}),
        help_text='Source interface for BGP peering (optional)'
    )


class VXLANTunnelForm(forms.Form):
    tunnel_id = forms.IntegerField(
        min_value=1,
        max_value=4095,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        help_text='VXLAN tunnel interface ID'
    )
    source_ip = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10.1.1.1'}),
        help_text='Source IP address for VXLAN tunnel'
    )
    destination_ip = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10.1.1.2'}),
        help_text='Destination IP address for VXLAN tunnel'
    )
    vni = forms.IntegerField(
        min_value=1,
        max_value=16777215,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '10001'}),
        help_text='VXLAN Network Identifier (VNI)'
    )


class NVEInterfaceForm(forms.Form):
    nve_id = forms.IntegerField(
        min_value=1,
        max_value=4095,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        help_text='NVE interface ID'
    )
    source_ip = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10.1.1.1'}),
        help_text='Source IP address for NVE interface'
    )
    vni_mappings = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': '10001:100\n10002:200'}),
        help_text='VNI to Bridge Domain mappings (VNI:BD_ID, one per line)'
    )


class VXLANGatewayForm(forms.Form):
    bridge_domain_id = forms.IntegerField(
        min_value=1,
        max_value=16777215,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}),
        help_text='Bridge Domain ID'
    )
    gateway_ip = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '192.168.100.1'}),
        help_text='Gateway IP address'
    )
    subnet_mask = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '255.255.255.0'}),
        help_text='Subnet mask for the gateway'
    )
    vbdif_id = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=16777215,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}),
        help_text='VBDIF interface ID (optional, defaults to BD ID)'
    )


class VXLANAccessPortForm(forms.Form):
    interface = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control interface-select'}),
        help_text='Interface to configure as VXLAN access port'
    )
    bridge_domain_id = forms.IntegerField(
        min_value=1,
        max_value=16777215,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}),
        help_text='Bridge Domain ID to assign to the interface'
    )


class DataCenterFabricForm(forms.Form):
    DEVICE_ROLE_CHOICES = [
        ('spine', 'Spine Switch'),
        ('leaf', 'Leaf Switch'),
        ('border_leaf', 'Border Leaf (External Connectivity)')
    ]
    
    fabric_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DC1_FABRIC'}),
        help_text='Name of the fabric to add this device to'
    )
    
    device_role = forms.ChoiceField(
        choices=DEVICE_ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Role of this device in the datacenter fabric'
    )
    device_id = forms.IntegerField(
        min_value=1,
        max_value=255,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
        help_text='Unique device ID in the fabric'
    )
    as_number = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        initial=65000,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65000'}),
        help_text='BGP AS number for the fabric'
    )
    loopback_ip = forms.GenericIPAddressField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10.255.255.1'}),
        help_text='Loopback IP address (auto-generated if empty)'
    )
    underlay_ip_range = forms.CharField(
        max_length=20,
        initial='10.0.0.0/30',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10.0.0.0/30'}),
        help_text='IP range for underlay point-to-point links'
    )
    spine_interfaces = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': '100GE1/0/1\n100GE1/0/2'}),
        help_text='Interfaces connecting to spines/leaves (one per line)'
    )


class TenantNetworkForm(forms.Form):
    tenant_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'WEB_TIER'}),
        help_text='Tenant network name (will be used for EVPN instance)'
    )
    vni = forms.IntegerField(
        min_value=1,
        max_value=16777215,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '10001'}),
        help_text='VXLAN Network Identifier (VNI)'
    )
    vlan_id = forms.IntegerField(
        min_value=1,
        max_value=4094,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}),
        help_text='VLAN ID for local switching'
    )
    gateway_ip = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '192.168.100.1'}),
        help_text='Gateway IP address for the tenant network'
    )
    subnet_mask = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '255.255.255.0'}),
        help_text='Subnet mask for the tenant network'
    )
    route_target = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65000:10001'}),
        help_text='Route target (auto-generated if empty)'
    )
    access_interfaces = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'GE1/0/1\nGE1/0/2'}),
        help_text='Access interfaces for this tenant (one per line, optional)'
    )
    advertise_external = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Advertise this tenant network to external networks'
    )


class ExternalConnectivityForm(forms.Form):
    vrf_name = forms.CharField(
        max_length=50,
        initial='EXTERNAL_VRF',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EXTERNAL_VRF'}),
        help_text='VRF name for external connectivity'
    )
    external_interface = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control interface-select'}),
        help_text='Interface connecting to external network (WAN/DCI)'
    )
    external_ip = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '203.0.113.1'}),
        help_text='IP address for external connectivity'
    )
    external_mask = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '255.255.255.252'}),
        help_text='Subnet mask for external interface'
    )
    external_peer_ip = forms.GenericIPAddressField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '203.0.113.2'}),
        help_text='External BGP peer IP address'
    )
    external_as = forms.IntegerField(
        min_value=1,
        max_value=4294967295,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65001'}),
        help_text='External BGP peer AS number'
    )
    route_distinguisher = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65000:999'}),
        help_text='Route distinguisher for external VRF (auto if empty)'
    )
    route_target = forms.CharField(
        max_length=20,
        initial='65000:999',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65000:999'}),
        help_text='Route target for external connectivity'
    )


class AEForm(forms.Form):
    ae_name = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ae0'}), help_text='AE interface name (e.g., ae0)')
    lacp = forms.BooleanField(initial=True, required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), help_text='Enable LACP')
    members = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'ge-0/0/0\nge-0/0/1'}), help_text='Member interfaces (one per line)')
    unit = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}), help_text='Unit number')
    ip_address = forms.GenericIPAddressField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10.1.1.1'}), help_text='IP address (optional)')
    prefix_length = forms.IntegerField(min_value=1, max_value=128, initial=24, widget=forms.NumberInput(attrs={'class': 'form-control'}), help_text='IP prefix length')
    description = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}), help_text='Description (optional)')

class HuaweiEthTrunkForm(forms.Form):
    trunk_id = forms.IntegerField(min_value=1, max_value=4096, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}), help_text='Eth-Trunk ID (e.g., 1)')
    mode = forms.ChoiceField(choices=[('lacp', 'LACP (dynamic)'), ('lacp-static', 'LACP Static')], initial='lacp', widget=forms.Select(attrs={'class': 'form-control'}), help_text='Aggregation mode')
    mlag_id = forms.IntegerField(required=False, min_value=1, max_value=65535, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}), help_text='M-LAG domain ID (optional)')
    allowed_vlans = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1-10,20,30-40'}), help_text='Allowed VLANs for trunk (optional)')
    members = forms.CharField(required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'GE1/0/1\nGE1/0/2'}), help_text='Member interfaces (one per line)')
    description = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}), help_text='Description (optional)')

class HuaweiEthTrunkMLAGForm(forms.Form):
    primary_device = forms.ModelChoiceField(queryset=Device.objects.filter(is_active=True), label='Primary Switch')
    peer_device = forms.ModelChoiceField(queryset=Device.objects.filter(is_active=True), label='Peer Switch')
    trunk_id = forms.IntegerField(min_value=1, max_value=4096, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}), help_text='Eth-Trunk ID (e.g., 1)')
    mode = forms.ChoiceField(choices=[('lacp', 'LACP (dynamic)'), ('lacp-static', 'LACP Static')], initial='lacp', widget=forms.Select(attrs={'class': 'form-control'}), help_text='Aggregation mode')
    mlag_id = forms.IntegerField(required=False, min_value=1, max_value=65535, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}), help_text='M-LAG domain ID (optional)')
    allowed_vlans = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1-10,20,30-40'}), help_text='Allowed VLANs for trunk (optional)')
    members_primary = forms.CharField(required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'GE1/0/1\nGE1/0/2'}), label='Primary members', help_text='Member interfaces on primary (one per line)')
    members_peer = forms.CharField(required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'GE2/0/1\nGE2/0/2'}), label='Peer members', help_text='Member interfaces on peer (one per line)')
    description = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}), help_text='Description (optional)')

    def clean(self):
        cleaned = super().clean()
        p = cleaned.get('primary_device')
        q = cleaned.get('peer_device')
        if p and q and p.id == q.id:
            raise forms.ValidationError('Primary and Peer switches must be different devices.')
        # Optionally enforce Huawei types
        return cleaned

class L2VPWSForm(forms.Form):
    service_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VPWS_100'}), help_text='VPWS instance name')
    local_if = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}), help_text='Local interface')
    remote_ip = forms.GenericIPAddressField(widget=forms.TextInput(attrs={'class': 'form-control'}), help_text='Remote PE IP')
    vc_id = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}), help_text='VC ID (must match on both PEs)')
    description = forms.CharField(max_length=255, required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Customer 100'}), help_text='Optional description')

class L2VPNSVCForm(forms.Form):
    service_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VPLS_200'}), help_text='VPLS instance name')
    vpls_id = forms.IntegerField(min_value=10, max_value=16777214, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '200'}), help_text='VPLS ID (VLAN ID 10–16777214)')
    rd = forms.CharField(max_length=21, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65100:200'}), help_text='Route distinguisher')
    rt_both = forms.CharField(max_length=21, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65100:200'}), help_text='Import/Export target (same value)')
    description = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}), help_text='Optional description')

class EVPNInstanceForm(forms.Form):
    instance_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EVPN_VPLS_200'}), help_text='EVPN instance name')
    vpls_id = forms.IntegerField(min_value=10, max_value=16777214, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '200'}), help_text='VPLS ID')
    rd = forms.CharField(max_length=21, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '65100:200'}), help_text='Route distinguisher')
    rt_target = forms.IntegerField(min_value=1, max_value=4294967295, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '65100'}), help_text='Route target ASN')
    rt_id = forms.IntegerField(min_value=1, max_value=65535, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '200'}), help_text='Route target ID')
    encapsulation = forms.ChoiceField(choices=[('mpls', 'MPLS')], initial='mpls', widget=forms.Select(attrs={'class': 'form-control'}), help_text='Encapsulation type')
    replication_type = forms.ChoiceField(choices=[('ingress', 'Ingress'), ('egress', 'Egress')], initial='ingress', widget=forms.Select(attrs={'class': 'form-control'}), help_text='Replication type')
    description = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}), help_text='Optional description')

class BridgeDomainForm(forms.Form):
    bd_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'BD_Customer_100'}), help_text='Bridge domain name')
    vlan_id = forms.IntegerField(min_value=10, max_value=16777214, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}), help_text='VLAN ID (10–16777214)')
    interface = forms.ChoiceField(required=False, widget=forms.Select(attrs={'class': 'form-control interface-select'}), help_text='Interface to assign to BD (optional)')
    description = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}), help_text='Optional description')

class MultiTenantDeploymentForm(forms.Form):
    fabric_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DC1_FABRIC'}),
        help_text='Name for the datacenter fabric deployment'
    )
    tenant_networks_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 12,
            'placeholder': '''[
  {
    "name": "WEB_TIER",
    "vni": 10001,
    "vlan_id": 100,
    "gateway_ip": "192.168.100.1",
    "subnet_mask": "255.255.255.0",
    "access_interfaces": ["GE1/0/1", "GE1/0/2"],
    "advertise_external": true
  },
  {
    "name": "APP_TIER",
    "vni": 10002,
    "vlan_id": 200,
    "gateway_ip": "192.168.200.1",
    "subnet_mask": "255.255.255.0",
    "access_interfaces": ["GE1/0/3", "GE1/0/4"],
    "advertise_external": false
  }
]'''
        }),
        help_text='JSON configuration for all tenant networks'
    )
    deploy_to_devices = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'leaf-01\nleaf-02\nleaf-03'
        }),
        help_text='Device names to deploy tenant networks to (one per line)'
    )


class FullFabricDeploymentForm(forms.Form):
    fabric_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DC1_FABRIC'}),
        help_text='Identifier for this fabric deployment'
    )
    underlay_ip_range = forms.CharField(
        max_length=20,
        initial='10.0.0.0/30',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10.0.0.0/30'}),
        help_text='Base /30 pool used for spine-leaf links'
    )
    devices_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 12,
            'placeholder': '''[
  {"name": "spine-01", "role": "spine", "device_id": 1,  "as_number": 65000, "spine_interfaces": ["100GE1/0/1", "100GE1/0/2"]},
  {"name": "leaf-01",  "role": "leaf",  "device_id": 11, "as_number": 65000, "spine_interfaces": ["GE1/0/51", "GE1/0/52"]}
]'''
        }),
        help_text='JSON array of devices with role, unique device_id, per-device as_number, and uplink interfaces'
    )
    links_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': '''[
  {"spine": "spine-01", "spine_interface": "100GE1/0/1", "leaf": "leaf-01", "leaf_interface": "GE1/0/51"},
  {"spine": "spine-02", "spine_interface": "100GE1/0/1", "leaf": "leaf-01", "leaf_interface": "GE1/0/52"}
]'''
        }),
        help_text='Optional: explicit spine↔leaf link mapping (each entry defines a /30 link)'
    )
    tenant_networks_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': '''[
  {"name": "WEB", "vni": 10001, "vlan_id": 100, "gateway_ip": "192.168.100.1", "subnet_mask": "255.255.255.0", "access_interfaces": []}
]'''
        }),
        help_text='Optional: Tenant networks to deploy to all leaves/border leaves'
    )
    skip_validation = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Skip pre-check validation on devices'
    )

    def clean_devices_json(self):
        raw = self.cleaned_data['devices_json']
        try:
            data = json.loads(raw)
            if not isinstance(data, list) or not data:
                raise forms.ValidationError('Provide a non-empty JSON array of devices.')
            for d in data:
                if not all(k in d for k in ['name', 'role', 'device_id', 'as_number', 'spine_interfaces']):
                    raise forms.ValidationError("Each device needs 'name', 'role', 'device_id', 'as_number', 'spine_interfaces'.")
                if d['role'] not in ['spine', 'leaf', 'border_leaf']:
                    raise forms.ValidationError("Device role must be spine, leaf or border_leaf.")
                if not isinstance(d['spine_interfaces'], list):
                    raise forms.ValidationError("'spine_interfaces' must be a list of interface names.")
            return data
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format.')

    def clean_links_json(self):
        raw = self.cleaned_data.get('links_json')
        if not raw:
            return []
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                raise forms.ValidationError('Links must be a JSON array.')
            for i, l in enumerate(data):
                if not all(k in l for k in ['spine', 'spine_interface', 'leaf', 'leaf_interface']):
                    raise forms.ValidationError(f'Link #{i+1} must include spine, spine_interface, leaf, leaf_interface.')
            return data
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format for links.')

    def clean_tenant_networks_json(self):
        raw = self.cleaned_data.get('tenant_networks_json')
        if not raw:
            return []
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                raise forms.ValidationError('Tenant networks must be a JSON array.')
            required = {'name','vni','vlan_id','gateway_ip','subnet_mask'}
            for t in data:
                if not required.issubset(t.keys()):
                    raise forms.ValidationError('Each tenant must include name,vni,vlan_id,gateway_ip,subnet_mask.')
            return data
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format for tenant networks.')
