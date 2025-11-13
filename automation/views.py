from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction
import json
import threading
from .models import Device, NetworkTask, TaskResult
from .evpn_l2vpn import EVPNManager
from .forms import (
    DeviceForm, VLANCreateForm, VLANDeleteForm, InterfaceConfigForm,
    StaticRouteForm, OSPFConfigForm, DeviceTestForm,
    VRFCreateForm, VRFAssignInterfaceForm, BGPNeighborForm, BGPNetworkForm, BGPVRFConfigForm,
    VLANInterfaceConfigForm, BGPRouteReflectorForm, BGPConfederationForm, BGPMultipathForm,
    OSPFAreaForm, OSPFAuthenticationForm, EVPNInstanceForm, BGPEVPNForm, VXLANTunnelForm,
    NVEInterfaceForm, VXLANGatewayForm, VXLANAccessPortForm, DataCenterFabricForm,
    TenantNetworkForm, ExternalConnectivityForm, MultiTenantDeploymentForm, FullFabricDeploymentForm,
    DeviceSelectionForm, ShowRoutesForm, AEForm, L2VPWSForm, L2VPNSVCForm, BridgeDomainForm,
    HuaweiEthTrunkMLAGForm, InterfaceIPv6Form, VLANInterfaceIPv6Form, StaticRouteV6Form, OSPFv3ConfigForm
)
from .network_automation import execute_network_task


def healthcheck(request):
    return JsonResponse({"status": "ok"})


def index(request):
    """Dashboard view showing overview of devices and recent tasks"""
    device_count = Device.objects.count()
    active_devices = Device.objects.filter(is_active=True).count()
    recent_tasks = NetworkTask.objects.order_by('-created_at')[:5]
    
    # Task status statistics
    task_stats = {
        'pending': NetworkTask.objects.filter(status='pending').count(),
        'running': NetworkTask.objects.filter(status='running').count(),
        'completed': NetworkTask.objects.filter(status='completed').count(),
        'failed': NetworkTask.objects.filter(status='failed').count(),
    }
    
    context = {
        'device_count': device_count,
        'active_devices': active_devices,
        'recent_tasks': recent_tasks,
        'task_stats': task_stats,
    }
    return render(request, 'automation/index.html', context)


def device_list(request):
    """List all devices with pagination"""
    devices = Device.objects.all().order_by('name')
    paginator = Paginator(devices, 10)  # Show 10 devices per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'automation/device_list.html', context)


@login_required
def device_create(request):
    """Create a new device"""
    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Device "{form.cleaned_data["name"]}" created successfully!')
            return redirect('device_list')
    else:
        form = DeviceForm()
    
    context = {'form': form, 'title': 'Add New Device'}
    return render(request, 'automation/device_form.html', context)


@login_required
def device_edit(request, device_id):
    """Edit an existing device"""
    device = get_object_or_404(Device, id=device_id)
    
    if request.method == 'POST':
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            form.save()
            messages.success(request, f'Device "{device.name}" updated successfully!')
            return redirect('device_list')
    else:
        form = DeviceForm(instance=device)
    
    context = {'form': form, 'device': device, 'title': f'Edit {device.name}'}
    return render(request, 'automation/device_form.html', context)


@login_required
def device_delete(request, device_id):
    """Delete a device"""
    device = get_object_or_404(Device, id=device_id)
    
    if request.method == 'POST':
        device_name = device.name
        device.delete()
        messages.success(request, f'Device "{device_name}" deleted successfully!')
        return redirect('device_list')
    
    context = {'device': device}
    return render(request, 'automation/device_confirm_delete.html', context)


def device_detail(request, device_id):
    """View device details and recent tasks"""
    device = get_object_or_404(Device, id=device_id)
    recent_tasks = NetworkTask.objects.filter(device=device).order_by('-created_at')[:10]
    
    context = {
        'device': device,
        'recent_tasks': recent_tasks,
    }
    return render(request, 'automation/device_detail.html', context)


@login_required
def device_test(request):
    """Test device connectivity"""
    if request.method == 'POST':
        form = DeviceTestForm(request.POST)
        if form.is_valid():
            device = form.cleaned_data['device']
            # Test connectivity by running show version
            success, result, error = execute_network_task(
                device.get_connection_params(),
                'show_version',
                {}
            )
            
            if success:
                device.last_connected = timezone.now()
                device.save()
                messages.success(request, f'Successfully connected to {device.name}!')
                context = {
                    'form': DeviceTestForm(),
                    'test_result': result,
                    'device_tested': device
                }
            else:
                messages.error(request, f'Failed to connect to {device.name}: {error}')
                context = {'form': form}
    else:
        form = DeviceTestForm()
        context = {'form': form}
    
    return render(request, 'automation/device_test.html', context)


def task_list(request):
    """List all tasks with filtering and pagination"""
    tasks = NetworkTask.objects.all().order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    # Filter by device if provided
    device_filter = request.GET.get('device')
    if device_filter:
        tasks = tasks.filter(device_id=device_filter)
    
    paginator = Paginator(tasks, 20)  # Show 20 tasks per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get devices for filter dropdown
    devices = Device.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'devices': devices,
        'current_status': status_filter,
        'current_device': device_filter,
        'status_choices': NetworkTask.STATUS_CHOICES,
    }
    return render(request, 'automation/task_list.html', context)


def task_detail(request, task_id):
    """View task details and results"""
    task = get_object_or_404(NetworkTask, id=task_id)
    
    try:
        task_result = task.taskresult
    except TaskResult.DoesNotExist:
        task_result = None
    
    context = {
        'task': task,
        'task_result': task_result,
    }
    return render(request, 'automation/task_detail.html', context)


def execute_task_async(task):
    """Execute network task asynchronously"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting async execution for task {task.id}: {task.task_type}")
    task.status = 'running'
    task.started_at = timezone.now()
    task.save()
    
    try:
        success, result, error = execute_network_task(
            task.device.get_connection_params(),
            task.task_type,
            task.parameters
        )
        
        task.completed_at = timezone.now()
        if success:
            task.status = 'completed'
            task.result = result
            
            # Create task result
            TaskResult.objects.create(
                task=task,
                output=result,
                success=True,
                execution_time=(task.completed_at - task.started_at).total_seconds()
            )
        else:
            task.status = 'failed'
            task.error_message = error
            
            TaskResult.objects.create(
                task=task,
                output=error,
                success=False,
                execution_time=(task.completed_at - task.started_at).total_seconds()
            )
        
        task.save()
        
    except Exception as e:
        task.status = 'failed'
        task.error_message = str(e)
        task.completed_at = timezone.now()
        task.save()


@login_required
def vlan_create(request):
    """Create VLAN on selected devices"""
    if request.method == 'POST':
        form = VLANCreateForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='vlan_create',
                parameters={
                    'vlan_id': form.cleaned_data['vlan_id'],
                    'vlan_name': form.cleaned_data.get('vlan_name', '')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'VLAN creation task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = VLANCreateForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Create VLAN',
        'action': 'Create'
    }
    return render(request, 'automation/vlan_form.html', context)


@login_required
def vlan_delete(request):
    """Delete VLAN from selected devices"""
    if request.method == 'POST':
        form = VLANDeleteForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='vlan_delete',
                parameters={'vlan_id': form.cleaned_data['vlan_id']},
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'VLAN deletion task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = VLANDeleteForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Delete VLAN',
        'action': 'Delete'
    }
    return render(request, 'automation/vlan_form.html', context)


@login_required
def interface_config(request):
    """Configure interface on selected device"""
    if request.method == 'POST':
        form = InterfaceConfigForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Prepare parameters based on mode
            parameters = {
                'interface': form.cleaned_data['interface'],
                'mode': form.cleaned_data['mode']
            }
            
            if form.cleaned_data['mode'] == 'access':
                parameters['vlan_id'] = form.cleaned_data['vlan_id']
            elif form.cleaned_data['mode'] == 'trunk':
                parameters['allowed_vlans'] = form.cleaned_data.get('allowed_vlans', 'all')
            elif form.cleaned_data['mode'] == 'ip':
                parameters['ip_address'] = form.cleaned_data['ip_address']
                parameters['subnet_mask'] = form.cleaned_data['subnet_mask']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='interface_config',
                parameters=parameters,
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'Interface configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = InterfaceConfigForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure Interface'
    }
    return render(request, 'automation/interface_form.html', context)


@login_required
def routing_static(request):
    """Configure static routing on selected device"""
    if request.method == 'POST':
        form = StaticRouteForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='routing_static',
                parameters={
                    'action': form.cleaned_data['action'],
                    'network': form.cleaned_data['network'],
                    'mask': form.cleaned_data['mask'],
                    'next_hop': form.cleaned_data['next_hop'],
                    'vrf_name': form.cleaned_data.get('vrf_name')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'Static routing task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = StaticRouteForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure Static Route'
    }
    return render(request, 'automation/routing_form.html', context)


@login_required
def routing_ospf(request):
    """Configure OSPF routing on selected device"""
    if request.method == 'POST':
        form = OSPFConfigForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='routing_ospf',
                parameters={
                    'process_id': form.cleaned_data['process_id'],
                    'router_id': form.cleaned_data['router_id'],
                    'networks': form.cleaned_data['networks'],
                    'vrf_name': form.cleaned_data.get('vrf_name')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'OSPF configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = OSPFConfigForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure OSPF'
    }
    return render(request, 'automation/ospf_form.html', context)


@login_required
def show_command(request, command_type):
    """Execute show commands on selected device"""
    import logging
    logger = logging.getLogger(__name__)
    
    command_map = {
        'version': 'show_version',
        'interfaces': 'show_interfaces',
        'vlan': 'show_vlan',
        'routes': 'show_routes',
        'config': 'backup_config'
    }
    
    if command_type not in command_map:
        messages.error(request, 'Invalid command type')
        return redirect('index')
    
    if request.method == 'POST':
        logger.info(f"Show command POST request: {command_type}, User: {request.user}")
        
        # Use special form for routes command to support VRF
        if command_type == 'routes':
            from .forms import ShowRoutesForm
            form = ShowRoutesForm(request.POST)
            if form.is_valid():
                device = form.cleaned_data['device']
                vrf_name = form.cleaned_data.get('vrf_name')
                logger.info(f"Device selected: {device.name} ({device.device_type}), VRF: {vrf_name or 'global'}")
                
                # Create network task with VRF parameter
                parameters = {}
                if vrf_name:
                    parameters['vrf_name'] = vrf_name
                
                task = NetworkTask.objects.create(
                    device=device,
                    task_type=command_map[command_type],
                    parameters=parameters,
                    created_by=request.user
                )
                logger.info(f"Task created: ID {task.id}, Type: {task.task_type}, Parameters: {parameters}")
                
                # Execute task asynchronously
                thread = threading.Thread(target=execute_task_async, args=(task,))
                thread.start()
                logger.info(f"Background thread started for task {task.id}")
                
                messages.success(request, f'Routes command submitted for {device.name}{f" (VRF: {vrf_name})" if vrf_name else ""}')
                return redirect('task_detail', task_id=task.id)
            else:
                logger.error(f"Routes form validation failed: {form.errors}")
                messages.error(request, 'Please correct the form errors')
        else:
            # Use regular device selection form for other commands
            device_form = DeviceSelectionForm(request.POST)
            
            if device_form.is_valid():
                device = device_form.cleaned_data['device']
                logger.info(f"Device selected: {device.name} ({device.device_type})")
                
                # Create network task
                task = NetworkTask.objects.create(
                    device=device,
                    task_type=command_map[command_type],
                    parameters={},
                    created_by=request.user
                )
                logger.info(f"Task created: ID {task.id}, Type: {task.task_type}")
                
                # Execute task asynchronously
                thread = threading.Thread(target=execute_task_async, args=(task,))
                thread.start()
                logger.info(f"Background thread started for task {task.id}")
                
                messages.success(request, f'{command_type.title()} command submitted for {device.name}')
                return redirect('task_detail', task_id=task.id)
            else:
                logger.error(f"Device form validation failed: {device_form.errors}")
                messages.error(request, 'Please select a device')
    else:
        # Initialize forms based on command type
        if command_type == 'routes':
            from .forms import ShowRoutesForm
            form = ShowRoutesForm()
        else:
            device_form = DeviceSelectionForm()
    
    if command_type == 'routes':
        context = {
            'form': form,
            'title': f'Show {command_type.title()}',
            'command_type': command_type,
            'supports_vrf': True
        }
    else:
        context = {
            'device_form': device_form,
            'title': f'Show {command_type.title()}',
            'command_type': command_type,
            'supports_vrf': False
        }
    return render(request, 'automation/show_command_form.html', context)


@require_http_methods(["GET"])
def api_task_status(request, task_id):
    """API endpoint to get task status (for AJAX polling)"""
    try:
        task = NetworkTask.objects.get(id=task_id)
        data = {
            'status': task.status,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'result': task.result,
            'error_message': task.error_message
        }
        return JsonResponse(data)
    except NetworkTask.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)


@require_http_methods(["GET"])
def api_device_interfaces(request, device_id):
    """API endpoint to get device interfaces"""
    try:
        device = Device.objects.get(id=device_id, is_active=True)
        
        # Execute show interfaces command
        success, result, error = execute_network_task(
            device.get_connection_params(),
            'show_interfaces',
            {}
        )
        
        if not success:
            return JsonResponse({'error': f'Failed to get interfaces: {error}'}, status=500)
        
        # Parse interfaces from the output
        interfaces = parse_interfaces_from_output(result, device.device_type)
        
        return JsonResponse({'interfaces': interfaces})
        
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Device not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_device_vrfs(request, device_id):
    """API endpoint to get device VRFs"""
    try:
        device = Device.objects.get(id=device_id, is_active=True)
        
        # Execute show VRFs command
        if 'cisco' in device.device_type:
            command = 'show ip vrf'
        elif 'huawei' in device.device_type:
            command = 'display ip vpn-instance'
        else:
            return JsonResponse({'error': f'Unsupported device type: {device.device_type}'}, status=400)
        
        from .network_automation import NetworkDeviceManager
        try:
            device_manager = NetworkDeviceManager(device.get_connection_params())
            device_manager.connect()
            result = device_manager.execute_command(command)
            device_manager.disconnect()
            
            # Parse VRFs from the output
            vrfs = parse_vrfs_from_output(result, device.device_type)
            
            return JsonResponse({'vrfs': vrfs})
            
        except Exception as e:
            return JsonResponse({'vrfs': []})  # Return empty list if VRFs can't be retrieved
        
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Device not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def parse_interfaces_from_output(output, device_type):
    """Parse interface names from show interfaces output"""
    interfaces = []
    
    if 'cisco' in device_type:
        # Parse Cisco interface output
        for line in output.split('\n'):
            line = line.strip()
            if line and not line.startswith(' ') and ' is ' in line:
                interface_name = line.split(' is ')[0].strip()
                if (interface_name and not interface_name.startswith('Interface') and
                    (interface_name.startswith(('GigabitEthernet', 'FastEthernet', 'Ethernet', 'TenGigabitEthernet', 
                                               'TenGigE', 'Loopback', 'Vlan', 'Serial', 'Tunnel')))):
                    interfaces.append(interface_name)
    
    elif 'huawei' in device_type:
        # Parse Huawei interface output
        import re
        for line in output.split('\n'):
            line = line.strip()
            if line and (line.startswith('GigabitEthernet') or line.startswith('Ethernet') or 
                        line.startswith('FastEthernet') or line.startswith('TenGigabitEthernet') or
                        line.startswith('100GE') or line.startswith('10GE') or
                        re.match(r'^G\d+/\d+/\d+', line) or  # Match G1/0/1 pattern
                        line.startswith('Vlanif') or line.startswith('LoopBack')):
                interface_name = line.split()[0]
                if interface_name:
                    interfaces.append(interface_name)
    
    # Remove duplicates and sort
    interfaces = sorted(list(set(interfaces)))
    
    # Add some common interface types if parsing failed
    if not interfaces:
        if 'cisco' in device_type:
            interfaces = [
                'GigabitEthernet0/0', 'GigabitEthernet0/1', 'GigabitEthernet0/2', 'GigabitEthernet0/3',
                'TenGigabitEthernet0/0', 'TenGigabitEthernet0/1',
                'FastEthernet0/0', 'FastEthernet0/1', 'Loopback0', 'Loopback1', 'Vlan1'
            ]
        elif 'huawei' in device_type:
            interfaces = [
                'GigabitEthernet0/0/1', 'GigabitEthernet0/0/2', 'GigabitEthernet0/0/3', 'GigabitEthernet0/0/4',
                '100GE1/0/1', '100GE1/0/2', '10GE1/0/1', '10GE1/0/2',
                'G1/0/1', 'G1/0/2', 'G1/0/3', 'G1/0/4',
                'Ethernet0/0/1', 'Ethernet0/0/2', 'LoopBack0', 'LoopBack1', 'Vlanif1'
            ]
    
    return interfaces


def parse_vrfs_from_output(output, device_type):
    """Parse VRF names from show VRF output"""
    vrfs = []
    
    if 'cisco' in device_type:
        # Parse Cisco VRF output
        for line in output.split('\n'):
            line = line.strip()
            if line and not line.startswith('Name') and not line.startswith('---'):
                parts = line.split()
                if parts and not parts[0].lower() in ['name', 'default']:
                    vrfs.append(parts[0])
    
    elif 'huawei' in device_type:
        # Parse Huawei VRF output
        for line in output.split('\n'):
            line = line.strip()
            if 'vpn-instance' in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.lower() == 'vpn-instance' and i + 1 < len(parts):
                        vrfs.append(parts[i + 1])
    
    # Remove duplicates and sort
    vrfs = sorted(list(set(vrfs)))
    
    return vrfs


@login_required
def vrf_create(request):
    """Create VRF on selected device"""
    if request.method == 'POST':
        form = VRFCreateForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='vrf_create',
                parameters={
                    'vrf_name': form.cleaned_data['vrf_name'],
                    'rd': form.cleaned_data.get('rd', ''),
                    'description': form.cleaned_data.get('description', ''),
                    'import_rt': form.cleaned_data.get('import_rt', ''),
                    'export_rt': form.cleaned_data.get('export_rt', '')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'VRF creation task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = VRFCreateForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Create VRF',
        'action': 'Create'
    }
    return render(request, 'automation/vrf_form.html', context)


@login_required
def vrf_assign_interface(request):
    """Assign VRF to interface on selected device"""
    if request.method == 'POST':
        form = VRFAssignInterfaceForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='vrf_assign_interface',
                parameters={
                    'vrf_name': form.cleaned_data['vrf_name'],
                    'interface': form.cleaned_data['interface'],
                    'ip_address': form.cleaned_data.get('ip_address', ''),
                    'subnet_mask': form.cleaned_data.get('subnet_mask', '')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'VRF interface assignment task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = VRFAssignInterfaceForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Assign VRF to Interface'
    }
    return render(request, 'automation/vrf_interface_form.html', context)


@login_required
def bgp_neighbor(request):
    """Configure BGP neighbor on selected device"""
    if request.method == 'POST':
        form = BGPNeighborForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='bgp_neighbor',
                parameters={
                    'as_number': form.cleaned_data['as_number'],
                    'neighbor_ip': form.cleaned_data['neighbor_ip'],
                    'remote_as': form.cleaned_data['remote_as'],
                    'vrf_name': form.cleaned_data.get('vrf_name', ''),
                    'description': form.cleaned_data.get('description', '')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'BGP neighbor configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = BGPNeighborForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure BGP Neighbor'
    }
    return render(request, 'automation/bgp_neighbor_form.html', context)


@login_required
def bgp_network(request):
    """Advertise network in BGP on selected device"""
    if request.method == 'POST':
        form = BGPNetworkForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='bgp_network',
                parameters={
                    'as_number': form.cleaned_data['as_number'],
                    'network': form.cleaned_data['network'],
                    'mask': form.cleaned_data['mask'],
                    'vrf_name': form.cleaned_data.get('vrf_name', '')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'BGP network advertisement task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = BGPNetworkForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Advertise BGP Network'
    }
    return render(request, 'automation/bgp_network_form.html', context)


@login_required
def bgp_vrf_config(request):
    """Configure BGP for VRF on selected device"""
    if request.method == 'POST':
        form = BGPVRFConfigForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='bgp_vrf_config',
                parameters={
                    'as_number': form.cleaned_data['as_number'],
                    'vrf_name': form.cleaned_data['vrf_name'],
                    'router_id': form.cleaned_data.get('router_id', ''),
                    'import_rt': form.cleaned_data.get('import_rt', ''),
                    'export_rt': form.cleaned_data.get('export_rt', '')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'BGP VRF configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = BGPVRFConfigForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure BGP for VRF'
    }
    return render(request, 'automation/bgp_vrf_form.html', context)


@login_required
def vlan_interface_config(request):
    """Configure VLAN interface (SVI) on selected device"""
    if request.method == 'POST':
        form = VLANInterfaceConfigForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='vlan_interface_config',
                parameters={
                    'vlan_id': form.cleaned_data['vlan_id'],
                    'ip_address': form.cleaned_data['ip_address'],
                    'subnet_mask': form.cleaned_data['subnet_mask'],
                    'vrf_name': form.cleaned_data.get('vrf_name'),
                    'description': form.cleaned_data.get('description'),
                    'enable_interface': form.cleaned_data.get('enable_interface', True)
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'VLAN interface configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = VLANInterfaceConfigForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure VLAN Interface'
    }
    return render(request, 'automation/vlan_interface_form.html', context)


@login_required
def bgp_route_reflector(request):
    """Configure BGP Route Reflector on selected device"""
    if request.method == 'POST':
        form = BGPRouteReflectorForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Process clients (one per line)
            clients_text = form.cleaned_data.get('clients', '')
            clients = [client.strip() for client in clients_text.split('\n') if client.strip()]
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='bgp_route_reflector',
                parameters={
                    'as_number': form.cleaned_data['as_number'],
                    'router_id': form.cleaned_data['router_id'],
                    'cluster_id': form.cleaned_data['cluster_id'],
                    'clients': clients
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'BGP Route Reflector configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = BGPRouteReflectorForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure BGP Route Reflector'
    }
    return render(request, 'automation/bgp_route_reflector_form.html', context)


@login_required
def bgp_confederation(request):
    """Configure BGP Confederation on selected device"""
    if request.method == 'POST':
        form = BGPConfederationForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Process confederation peers (one per line)
            peers_text = form.cleaned_data.get('confederation_peers', '')
            peers = [peer.strip() for peer in peers_text.split('\n') if peer.strip()]
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='bgp_confederation',
                parameters={
                    'as_number': form.cleaned_data['as_number'],
                    'confederation_id': form.cleaned_data['confederation_id'],
                    'confederation_peers': peers
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'BGP Confederation configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = BGPConfederationForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure BGP Confederation'
    }
    return render(request, 'automation/bgp_confederation_form.html', context)


@login_required
def bgp_multipath(request):
    """Configure BGP Multipath on selected device"""
    if request.method == 'POST':
        form = BGPMultipathForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='bgp_multipath',
                parameters={
                    'as_number': form.cleaned_data['as_number'],
                    'ebgp_paths': form.cleaned_data['ebgp_paths'],
                    'ibgp_paths': form.cleaned_data['ibgp_paths']
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'BGP Multipath configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = BGPMultipathForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure BGP Multipath'
    }
    return render(request, 'automation/bgp_multipath_form.html', context)


@login_required
def ospf_area(request):
    """Configure OSPF Area on selected device"""
    if request.method == 'POST':
        form = OSPFAreaForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='ospf_area',
                parameters={
                    'process_id': form.cleaned_data['process_id'],
                    'area_id': form.cleaned_data['area_id'],
                    'area_type': form.cleaned_data['area_type'],
                    'stub_default_cost': form.cleaned_data.get('stub_default_cost'),
                    'nssa_default_route': form.cleaned_data.get('nssa_default_route', False)
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'OSPF Area configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = OSPFAreaForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure OSPF Area'
    }
    return render(request, 'automation/ospf_area_form.html', context)


@login_required
def ospf_authentication(request):
    """Configure OSPF Authentication on selected device"""
    if request.method == 'POST':
        form = OSPFAuthenticationForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='ospf_authentication',
                parameters={
                    'process_id': form.cleaned_data['process_id'],
                    'area_id': form.cleaned_data.get('area_id'),
                    'interface': form.cleaned_data.get('interface'),
                    'auth_type': form.cleaned_data['auth_type'],
                    'key_id': form.cleaned_data['key_id'],
                    'password': form.cleaned_data['password']
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'OSPF Authentication configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = OSPFAuthenticationForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure OSPF Authentication'
    }
    return render(request, 'automation/ospf_authentication_form.html', context)


@login_required
def evpn_instance(request):
    """Configure EVPN Instance on selected device"""
    if request.method == 'POST':
        form = EVPNInstanceForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='evpn_instance',
                parameters={
                    'evpn_instance': form.cleaned_data['evpn_instance'],
                    'route_distinguisher': form.cleaned_data['route_distinguisher'],
                    'export_rt': form.cleaned_data['export_rt'],
                    'import_rt': form.cleaned_data['import_rt']
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'EVPN Instance configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = EVPNInstanceForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure EVPN Instance'
    }
    return render(request, 'automation/evpn_instance_form.html', context)


@login_required
def bgp_evpn(request):
    """Configure BGP EVPN on selected device"""
    if request.method == 'POST':
        form = BGPEVPNForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='bgp_evpn',
                parameters={
                    'as_number': form.cleaned_data['as_number'],
                    'neighbor_ip': form.cleaned_data['neighbor_ip'],
                    'source_interface': form.cleaned_data.get('source_interface')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'BGP EVPN configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = BGPEVPNForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure BGP EVPN'
    }
    return render(request, 'automation/bgp_evpn_form.html', context)


@login_required
def vxlan_tunnel(request):
    """Configure VXLAN Tunnel on selected device"""
    if request.method == 'POST':
        form = VXLANTunnelForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='vxlan_tunnel',
                parameters={
                    'tunnel_id': form.cleaned_data['tunnel_id'],
                    'source_ip': form.cleaned_data['source_ip'],
                    'destination_ip': form.cleaned_data['destination_ip'],
                    'vni': form.cleaned_data['vni']
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'VXLAN Tunnel configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = VXLANTunnelForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure VXLAN Tunnel'
    }
    return render(request, 'automation/vxlan_tunnel_form.html', context)


@login_required
def nve_interface(request):
    """Configure NVE Interface on selected device"""
    if request.method == 'POST':
        form = NVEInterfaceForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Process VNI mappings (one per line)
            vni_mappings_text = form.cleaned_data.get('vni_mappings', '')
            vni_mappings = []
            for line in vni_mappings_text.split('\n'):
                if ':' in line:
                    vni, bd = line.strip().split(':')
                    vni_mappings.append({'vni': vni.strip(), 'bridge_domain': bd.strip()})
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='nve_interface',
                parameters={
                    'nve_id': form.cleaned_data['nve_id'],
                    'source_ip': form.cleaned_data['source_ip'],
                    'vni_mappings': vni_mappings
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'NVE Interface configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = NVEInterfaceForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure NVE Interface'
    }
    return render(request, 'automation/nve_interface_form.html', context)


@login_required
def vxlan_gateway(request):
    """Configure VXLAN Gateway on selected device"""
    if request.method == 'POST':
        form = VXLANGatewayForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='vxlan_gateway',
                parameters={
                    'bridge_domain_id': form.cleaned_data['bridge_domain_id'],
                    'gateway_ip': form.cleaned_data['gateway_ip'],
                    'subnet_mask': form.cleaned_data['subnet_mask'],
                    'vbdif_id': form.cleaned_data.get('vbdif_id')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'VXLAN Gateway configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = VXLANGatewayForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure VXLAN Gateway'
    }
    return render(request, 'automation/vxlan_gateway_form.html', context)


@login_required
def vxlan_access_port(request):
    """Configure VXLAN Access Port on selected device"""
    if request.method == 'POST':
        form = VXLANAccessPortForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='vxlan_access_port',
                parameters={
                    'interface': form.cleaned_data['interface'],
                    'bridge_domain_id': form.cleaned_data['bridge_domain_id']
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'VXLAN Access Port configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = VXLANAccessPortForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure VXLAN Access Port'
    }
    return render(request, 'automation/vxlan_access_port_form.html', context)


@login_required
def datacenter_fabric(request):
    """Deploy Datacenter Fabric on selected device"""
    if request.method == 'POST':
        form = DataCenterFabricForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Process spine interfaces (one per line)
            interfaces_text = form.cleaned_data.get('spine_interfaces', '')
            interfaces = [iface.strip() for iface in interfaces_text.split('\n') if iface.strip()]
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='datacenter_fabric',
                parameters={
                    'device_role': form.cleaned_data['device_role'],
                    'device_id': form.cleaned_data['device_id'],
                    'as_number': form.cleaned_data['as_number'],
                    'loopback_ip': form.cleaned_data.get('loopback_ip'),
                    'underlay_ip_range': form.cleaned_data['underlay_ip_range'],
                    'spine_interfaces': interfaces
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'Datacenter Fabric deployment task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = DataCenterFabricForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Deploy Datacenter Fabric'
    }
    return render(request, 'automation/datacenter_fabric_form.html', context)


@login_required
def tenant_network(request):
    """Deploy Tenant Network on selected device"""
    if request.method == 'POST':
        form = TenantNetworkForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Process access interfaces (one per line)
            interfaces_text = form.cleaned_data.get('access_interfaces', '')
            interfaces = [iface.strip() for iface in interfaces_text.split('\n') if iface.strip()]
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='tenant_network',
                parameters={
                    'tenant_name': form.cleaned_data['tenant_name'],
                    'vni': form.cleaned_data['vni'],
                    'vlan_id': form.cleaned_data['vlan_id'],
                    'gateway_ip': form.cleaned_data['gateway_ip'],
                    'subnet_mask': form.cleaned_data['subnet_mask'],
                    'route_target': form.cleaned_data.get('route_target'),
                    'access_interfaces': interfaces,
                    'advertise_external': form.cleaned_data.get('advertise_external', False)
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'Tenant Network deployment task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = TenantNetworkForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Deploy Tenant Network'
    }
    return render(request, 'automation/tenant_network_form.html', context)


@login_required
def bgp_neighbor_v6(request):
    if request.method == 'POST':
        form = BGPNeighborForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            task = NetworkTask.objects.create(
                device=device,
                task_type='bgp_neighbor_v6',
                parameters={
                    'as_number': form.cleaned_data['as_number'],
                    'neighbor_ip': form.cleaned_data['neighbor_ip'],
                    'remote_as': form.cleaned_data['remote_as'],
                    'vrf_name': form.cleaned_data.get('vrf_name', ''),
                    'description': form.cleaned_data.get('description', '')
                },
                created_by=request.user
            )
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            messages.success(request, f'BGP IPv6 neighbor task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = BGPNeighborForm()
        device_form = DeviceSelectionForm()
    return render(request, 'automation/bgp_neighbor_form.html', {'form': form, 'device_form': device_form, 'title': 'Configure BGP Neighbor (IPv6)'})


@login_required
def bgp_network_v6(request):
    if request.method == 'POST':
        form = BGPNetworkForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            # Build IPv6 prefix robustly
            net = form.cleaned_data['network']
            mask = form.cleaned_data['mask']
            if '/' in net:
                prefix = net
            elif ':' in net and str(mask).isdigit():
                prefix = f"{net}/{int(mask)}"
            else:
                # Fallback: assume IPv4-like and compute prefix length
                try:
                    m = mask
                    parts = [int(p) for p in m.split('.')]
                    bits = sum(bin(p).count('1') for p in parts)
                    prefix = f"{net}/{bits}"
                except Exception:
                    prefix = net
            task = NetworkTask.objects.create(
                device=device,
                task_type='bgp_network_v6',
                parameters={
                    'as_number': form.cleaned_data['as_number'],
                    'prefix': prefix,
                    'vrf_name': form.cleaned_data.get('vrf_name', '')
                },
                created_by=request.user
            )
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            messages.success(request, f'BGP IPv6 network task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = BGPNetworkForm()
        device_form = DeviceSelectionForm()
    return render(request, 'automation/bgp_network_form.html', {'form': form, 'device_form': device_form, 'title': 'Advertise BGP Network (IPv6)'})


@login_required
def external_connectivity(request):
    """Configure External Connectivity on selected device"""
    if request.method == 'POST':
        form = ExternalConnectivityForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='external_connectivity',
                parameters={
                    'vrf_name': form.cleaned_data['vrf_name'],
                    'external_interface': form.cleaned_data['external_interface'],
                    'external_ip': form.cleaned_data['external_ip'],
                    'external_mask': form.cleaned_data['external_mask'],
                    'external_peer_ip': form.cleaned_data['external_peer_ip'],
                    'external_as': form.cleaned_data['external_as'],
                    'route_distinguisher': form.cleaned_data.get('route_distinguisher'),
                    'route_target': form.cleaned_data['route_target']
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'External Connectivity configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = ExternalConnectivityForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure External Connectivity'
    }
    return render(request, 'automation/external_connectivity_form.html', context)


@login_required
def multi_tenant_deployment(request):
    """Deploy Multi-Tenant Configuration on selected devices"""
    if request.method == 'POST':
        form = MultiTenantDeploymentForm(request.POST)
        
        if form.is_valid():
            # Parse tenant networks JSON
            try:
                tenant_networks = json.loads(form.cleaned_data['tenant_networks_json'])
            except json.JSONDecodeError:
                messages.error(request, 'Invalid JSON format for tenant networks')
                context = {'form': form, 'title': 'Deploy Multi-Tenant Configuration'}
                return render(request, 'automation/multi_tenant_deployment_form.html', context)
            
            # Process device names (one per line)
            device_names = [name.strip() for name in form.cleaned_data['deploy_to_devices'].split('\n') if name.strip()]
            
            # Get devices by name
            devices = Device.objects.filter(name__in=device_names, is_active=True)
            if not devices.exists():
                messages.error(request, 'No matching active devices found')
                context = {'form': form, 'title': 'Deploy Multi-Tenant Configuration'}
                return render(request, 'automation/multi_tenant_deployment_form.html', context)
            
            # Create tasks for each device
            task_ids = []
            for device in devices:
                task = NetworkTask.objects.create(
                    device=device,
                    task_type='multi_tenant_deployment',
                    parameters={
                        'fabric_name': form.cleaned_data['fabric_name'],
                        'tenant_networks': tenant_networks
                    },
                    created_by=request.user
                )
                task_ids.append(task.id)
                
                # Execute task asynchronously
                thread = threading.Thread(target=execute_task_async, args=(task,))
                thread.start()
            
            messages.success(request, f'Multi-Tenant deployment tasks submitted for {len(devices)} devices')
            # Redirect to the first task (could be improved to show all tasks)
            return redirect('task_detail', task_id=task_ids[0] if task_ids else 1)
    else:
        form = MultiTenantDeploymentForm()
    
    context = {
        'form': form,
        'title': 'Deploy Multi-Tenant Configuration'
    }
    return render(request, 'automation/multi_tenant_deployment_form.html', context)


@login_required
def huawei_eth_trunk_mlag(request):
    """Configure Huawei Eth-Trunk with M-LAG on two switches concurrently"""
    if request.method == 'POST':
        form = HuaweiEthTrunkMLAGForm(request.POST)
        if form.is_valid():
            p = form.cleaned_data['primary_device']
            q = form.cleaned_data['peer_device']
            trunk_id = form.cleaned_data['trunk_id']
            mode = form.cleaned_data.get('mode', 'lacp')
            mlag_id = form.cleaned_data.get('mlag_id')
            allowed_vlans = form.cleaned_data.get('allowed_vlans')
            desc = form.cleaned_data.get('description')
            members_p = [m.strip() for m in form.cleaned_data['members_primary'].split('\n') if m.strip()]
            members_q = [m.strip() for m in form.cleaned_data['members_peer'].split('\n') if m.strip()]

            task_p = NetworkTask.objects.create(
                device=p,
                task_type='huawei_eth_trunk',
                parameters={
                    'trunk_id': trunk_id,
                    'mode': mode,
                    'mlag_id': mlag_id,
                    'allowed_vlans': allowed_vlans,
                    'members': members_p,
                    'description': desc,
                },
                created_by=request.user
            )
            task_q = NetworkTask.objects.create(
                device=q,
                task_type='huawei_eth_trunk',
                parameters={
                    'trunk_id': trunk_id,
                    'mode': mode,
                    'mlag_id': mlag_id,
                    'allowed_vlans': allowed_vlans,
                    'members': members_q,
                    'description': desc,
                },
                created_by=request.user
            )

            t1 = threading.Thread(target=execute_task_async, args=(task_p,))
            t2 = threading.Thread(target=execute_task_async, args=(task_q,))
            t1.start(); t2.start()

            messages.success(request, f'Eth-Trunk{trunk_id} MLAG tasks submitted for {p.name} and {q.name}')
            return redirect('task_detail', task_id=task_p.id)
    else:
        form = HuaweiEthTrunkMLAGForm()
    return render(request, 'automation/huawei_eth_trunk_mlag_form.html', {'form': form, 'title': 'Huawei Eth-Trunk (M-LAG)'} )


@login_required
def interface_ipv6_config(request):
    if request.method == 'POST':
        form = InterfaceIPv6Form(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            task = NetworkTask.objects.create(
                device=device,
                task_type='interface_ipv6',
                parameters={
                    'interface': form.cleaned_data['interface'],
                    'ipv6_address': form.cleaned_data['ipv6_address'],
                    'prefix_length': form.cleaned_data['prefix_length']
                },
                created_by=request.user
            )
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            messages.success(request, f'IPv6 interface configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = InterfaceIPv6Form()
        device_form = DeviceSelectionForm()
    return render(request, 'automation/interface_ipv6_form.html', {'form': form, 'device_form': device_form, 'title': 'Configure IPv6 on Interface'})


@login_required
def vlan_interface_ipv6_config(request):
    if request.method == 'POST':
        form = VLANInterfaceIPv6Form(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            task = NetworkTask.objects.create(
                device=device,
                task_type='vlan_interface_ipv6',
                parameters={
                    'vlan_id': form.cleaned_data['vlan_id'],
                    'ipv6_address': form.cleaned_data['ipv6_address'],
                    'prefix_length': form.cleaned_data['prefix_length'],
                    'vrf_name': form.cleaned_data.get('vrf_name'),
                    'description': form.cleaned_data.get('description'),
                    'enable_interface': form.cleaned_data.get('enable_interface', True)
                },
                created_by=request.user
            )
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            messages.success(request, f'IPv6 VLAN interface configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = VLANInterfaceIPv6Form()
        device_form = DeviceSelectionForm()
    return render(request, 'automation/vlan_interface_ipv6_form.html', {'form': form, 'device_form': device_form, 'title': 'Configure IPv6 on VLAN Interface'})


@login_required
def routing_static_v6(request):
    if request.method == 'POST':
        form = StaticRouteV6Form(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            task = NetworkTask.objects.create(
                device=device,
                task_type='routing_static_v6',
                parameters={
                    'action': form.cleaned_data['action'],
                    'prefix': form.cleaned_data['prefix'],
                    'next_hop': form.cleaned_data['next_hop'],
                    'vrf_name': form.cleaned_data.get('vrf_name')
                },
                created_by=request.user
            )
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            messages.success(request, f'IPv6 static route task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = StaticRouteV6Form()
        device_form = DeviceSelectionForm()
    return render(request, 'automation/routing_static_v6_form.html', {'form': form, 'device_form': device_form, 'title': 'Static Route (IPv6)'})


@login_required
def routing_ospf_v6(request):
    if request.method == 'POST':
        form = OSPFv3ConfigForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            task = NetworkTask.objects.create(
                device=device,
                task_type='routing_ospf_v6',
                parameters={
                    'process_id': form.cleaned_data['process_id'],
                    'router_id': form.cleaned_data['router_id'],
                    'interfaces': form.cleaned_data['interfaces']
                },
                created_by=request.user
            )
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            messages.success(request, f'OSPFv3 configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = OSPFv3ConfigForm()
        device_form = DeviceSelectionForm()
    return render(request, 'automation/ospf_v6_form.html', {'form': form, 'device_form': device_form, 'title': 'Configure OSPFv3 (IPv6)'})


@login_required
def ae_config(request):
    """Configure Aggregated Ethernet (AE) interface on selected device"""
    if request.method == 'POST':
        form = AEForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            
            # Process members (one per line)
            members_text = form.cleaned_data.get('members', '')
            members = [m.strip() for m in members_text.split('\n') if m.strip()]
            
            # Create network task
            task = NetworkTask.objects.create(
                device=device,
                task_type='ae_config',
                parameters={
                    'ae_name': form.cleaned_data['ae_name'],
                    'lacp': form.cleaned_data['lacp'],
                    'members': members,
                    'unit': form.cleaned_data['unit'],
                    'ip_address': form.cleaned_data.get('ip_address'),
                    'prefix_length': form.cleaned_data.get('prefix_length'),
                    'description': form.cleaned_data.get('description')
                },
                created_by=request.user
            )
            
            # Execute task asynchronously
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            
            messages.success(request, f'AE configuration task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = AEForm()
        device_form = DeviceSelectionForm()
    
    context = {
        'form': form,
        'device_form': device_form,
        'title': 'Configure Aggregated Ethernet (AE)',
    }
    return render(request, 'automation/ae_form.html', context)


@login_required
def full_fabric_deploy(request):
    """Deploy the entire datacenter fabric at once across all selected devices.
    Pre-fills devices list with all active devices and allows per-device AS numbers.
    """
    if request.method == 'POST':
        form = FullFabricDeploymentForm(request.POST)
        if form.is_valid():
            devices_data = form.cleaned_data['devices_json']
            links_data = form.cleaned_data.get('links_json', [])
            tenant_networks = form.cleaned_data.get('tenant_networks_json', [])
            underlay_range = form.cleaned_data['underlay_ip_range']
            skip_validation = form.cleaned_data.get('skip_validation', False)

            # Resolve devices by name and submit a task per device
            task_ids = []
            name_to_device = {d.name: d for d in Device.objects.filter(is_active=True)}
            devices_by_name = {d['name']: d for d in devices_data}
            # Determine spine ASNs in stable order (by device_id) for mapping
            spines_sorted = sorted(
                [e for e in devices_data if e.get('role') == 'spine'],
                key=lambda x: x.get('device_id', 0)
            )
            spine_as_list = [s.get('as_number') for s in spines_sorted]

            # Assign link indices deterministically and enrich with peer AS/IDs/loopbacks
            indexed_links = []
            for i, l in enumerate(links_data):
                idx = l.get('link_index') or (i + 1)
                spine_name = l['spine']
                leaf_name = l['leaf']
                spine_entry = devices_by_name.get(spine_name, {})
                leaf_entry = devices_by_name.get(leaf_name, {})
                # Determine peer loopbacks (prefer explicit loopback_ip if present)
                spine_loop = spine_entry.get('loopback_ip') or (f"10.255.255.{spine_entry.get('device_id', 1)}" if spine_entry else None)
                leaf_loop = leaf_entry.get('loopback_ip') or (f"10.255.254.{leaf_entry.get('device_id', 1)}" if leaf_entry else None)
                indexed_links.append({
                    'link_index': idx,
                    'spine': spine_name,
                    'spine_interface': l['spine_interface'],
                    'spine_as': spine_entry.get('as_number'),
                    'spine_device_id': spine_entry.get('device_id'),
                    'spine_loopback_ip': spine_loop,
                    'leaf': leaf_name,
                    'leaf_interface': l['leaf_interface'],
                    'leaf_as': leaf_entry.get('as_number'),
                    'leaf_device_id': leaf_entry.get('device_id'),
                    'leaf_loopback_ip': leaf_loop
                })

            for entry in devices_data:
                dev_obj = name_to_device.get(entry['name'])
                if not dev_obj:
                    continue  # Skip unknown names silently

                # Base params common to all roles
                fabric_params = {
                    'device_role': entry['role'],
                    'device_id': entry['device_id'],
                    'as_number': entry['as_number'],  # per-device AS number
                    'loopback_ip': entry.get('loopback_ip') or None,
                    'underlay_ip_range': underlay_range,
                    'spine_interfaces': entry.get('spine_interfaces', []),
                    'tenant_networks': tenant_networks,
                    'skip_validation': skip_validation,
                }

                # Attach explicit underlay links for this device, if provided
                if indexed_links:
                    if entry.get('role') == 'spine':
                        my_links = [
                            {
                                'link_index': l['link_index'],
                                'local_interface': l['spine_interface'],
                                'peer_device': l['leaf'],
                                'peer_interface': l['leaf_interface'],
                                'peer_as': l.get('leaf_as'),
                                'peer_device_id': l.get('leaf_device_id'),
                                'peer_loopback_ip': l.get('leaf_loopback_ip')
                            }
                            for l in indexed_links if l['spine'] == entry['name']
                        ]
                    else:
                        my_links = [
                            {
                                'link_index': l['link_index'],
                                'local_interface': l['leaf_interface'],
                                'peer_device': l['spine'],
                                'peer_interface': l['spine_interface'],
                                'peer_as': l.get('spine_as'),
                                'peer_device_id': l.get('spine_device_id'),
                                'peer_loopback_ip': l.get('spine_loopback_ip')
                            }
                            for l in indexed_links if l['leaf'] == entry['name']
                        ]
                    fabric_params['underlay_links'] = sorted(my_links, key=lambda x: x['link_index'])

                # For leaves/border leaves, provide remote spine ASNs and link indices aligned with uplinks
                if entry.get('role') in ('leaf', 'border_leaf'):
                    if indexed_links:
                        # Order by link_index and map to spine ASNs by spine name
                        leaf_links = [l for l in indexed_links if l['leaf'] == entry['name']]
                        leaf_links_sorted = sorted(leaf_links, key=lambda x: x['link_index'])
                        spine_as_by_name = {s['name']: s['as_number'] for s in spines_sorted}
                        fabric_params['spine_peer_as_numbers'] = [spine_as_by_name.get(l['spine']) for l in leaf_links_sorted]
                    else:
                        uplinks = entry.get('spine_interfaces', [])
                        fabric_params['spine_peer_as_numbers'] = spine_as_list[:len(uplinks)]
                        # Determine spine indices per uplink: prefer explicit 'to_spines' (by name), else 1..N
                        to_spines = entry.get('to_spines') or []
                        if to_spines and isinstance(to_spines, list) and len(to_spines) == len(uplinks):
                            spine_name_to_index = {s['name']: i+1 for i, s in enumerate(spines_sorted)}
                            uplink_indices = [spine_name_to_index.get(n, i+1) for i, n in enumerate(to_spines)]
                        else:
                            uplink_indices = [i+1 for i in range(len(uplinks))]
                        fabric_params['uplink_spine_indices'] = uplink_indices
                task = NetworkTask.objects.create(
                    device=dev_obj,
                    task_type='datacenter_fabric',
                    parameters=fabric_params,
                    created_by=request.user
                )
                task_ids.append(task.id)

                thread = threading.Thread(target=execute_task_async, args=(task,))
                thread.start()

            messages.success(request, f'Full fabric deployment tasks submitted for {len(task_ids)} devices')
            return redirect('task_detail', task_id=task_ids[0] if task_ids else 1)
    else:
        # Build a sensible default devices list from active inventory
        devices = list(Device.objects.filter(is_active=True).order_by('name'))
        spines = [d for d in devices if 'spine' in d.name.lower()]
        border_leaves = [d for d in devices if 'border' in d.name.lower() and d not in spines]
        leaves = [d for d in devices if d not in spines and d not in border_leaves]

        entries = []
        # Assign IDs: spines start at 1, border leaves at 9x, leaves at 10+
        for idx, d in enumerate(spines, start=1):
            entries.append({'name': d.name, 'role': 'spine', 'device_id': idx, 'as_number': 65000, 'spine_interfaces': []})
        for idx, d in enumerate(border_leaves, start=90):
            entries.append({'name': d.name, 'role': 'border_leaf', 'device_id': idx, 'as_number': 65000, 'spine_interfaces': []})
        for idx, d in enumerate(leaves, start=10):
            entries.append({'name': d.name, 'role': 'leaf', 'device_id': idx, 'as_number': 65000, 'spine_interfaces': []})

        initial = {
            'devices_json': json.dumps(entries, indent=2),
            'tenant_networks_json': json.dumps([], indent=2),
        }
        form = FullFabricDeploymentForm(initial=initial)

    context = {
        'form': form,
        'title': 'Deploy Whole Datacenter Fabric'
    }
    return render(request, 'automation/full_fabric_deployment_form.html', context)


# API Views

def api_task_status(request, task_id):
    """API endpoint to get task status"""
    try:
        task = NetworkTask.objects.get(id=task_id)
        data = {
            'status': task.status,
            'progress': getattr(task, 'progress', 0),
            'message': task.error_message if task.status == 'failed' else ''
        }
        return JsonResponse(data)
    except NetworkTask.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)


def api_device_interfaces(request, device_id):
    """API endpoint to get device interfaces"""
    try:
        device = Device.objects.get(id=device_id, is_active=True)
        
        # Execute show interfaces command to get interface list
        success, result, error = execute_network_task(
            device.get_connection_params(),
            'show_interfaces',
            {}
        )
        
        if success:
            # Parse interfaces from the result
            interfaces = parse_interfaces_from_output(result, device.device_type)
            return JsonResponse({'interfaces': interfaces})
        else:
            return JsonResponse({'error': f'Failed to retrieve interfaces: {error}'}, status=500)
            
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Device not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_device_vrfs(request, device_id):
    """API endpoint to get device VRFs"""
    try:
        device = Device.objects.get(id=device_id, is_active=True)
        
        # Execute show VRF command to get VRF list
        success, result, error = execute_network_task(
            device.get_connection_params(),
            'show_vrfs',
            {}
        )
        
        if success:
            # Parse VRFs from the result
            vrfs = parse_vrfs_from_output(result, device.device_type)
            
            # Include raw output in debug mode for troubleshooting
            response_data = {'vrfs': vrfs}
            
            # Add debug info if requested
            if request.GET.get('debug') == '1':
                response_data['debug'] = {
                    'raw_output': result,
                    'device_type': device.device_type,
                    'output_length': len(result) if result else 0,
                    'parsed_vrfs_count': len(vrfs)
                }
            
            return JsonResponse(response_data)
        else:
            return JsonResponse({'error': f'Failed to retrieve VRFs: {error}'}, status=500)
            
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Device not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def parse_interfaces_from_output(output, device_type):
    """Parse interface names from show interfaces output"""
    interfaces = []
    
    if not output:
        return interfaces
    
    lines = output.split('\n')
    
    try:
        if device_type in ['huawei', 'huawei_vrpv8']:
            # Huawei interface parsing
            for line in lines:
                line = line.strip()
                if any(prefix in line for prefix in ['GigabitEthernet', '10GE', '25GE', '40GE', '100GE', 'Ethernet']):
                    # Extract interface name (first word)
                    parts = line.split()
                    if parts:
                        interface_name = parts[0]
                        if interface_name not in interfaces:
                            interfaces.append(interface_name)
        
        elif device_type in ['cisco_ios', 'cisco_xe']:
            # Cisco interface parsing
            for line in lines:
                line = line.strip()
                if any(prefix in line for prefix in ['GigabitEthernet', 'TenGigabitEthernet', 'FastEthernet', 'Ethernet']):
                    # Extract interface name (first word)
                    parts = line.split()
                    if parts:
                        interface_name = parts[0]
                        if interface_name not in interfaces:
                            interfaces.append(interface_name)
        
        elif device_type in ['juniper_mx', 'juniper_srx']:
            # Juniper interface parsing
            for line in lines:
                line = line.strip()
                if any(prefix in line for prefix in ['ge-', 'xe-', 'et-', 'ae']):
                    # Extract interface name (first word)
                    parts = line.split()
                    if parts:
                        interface_name = parts[0]
                        if interface_name not in interfaces:
                            interfaces.append(interface_name)
    
    except Exception:
        # Fallback: return empty list if parsing fails
        pass
    
    return sorted(interfaces)


def parse_vrfs_from_output(output, device_type):
    """Parse VRF names from show VRF output with improved logic and debugging"""
    vrfs = []
    
    if not output:
        return vrfs
    
    # Log the raw output for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Parsing VRFs from {device_type} output (length: {len(output)})")
    logger.debug(f"Raw VRF output: {repr(output[:500])}...")  # First 500 chars for debugging
    
    lines = output.split('\n')
    logger.info(f"Processing {len(lines)} lines for VRF parsing")
    
    try:
        if device_type in ['huawei', 'huawei_vrpv8']:
            vrfs = parse_huawei_vrfs(lines, logger)
        elif device_type in ['cisco_ios', 'cisco_xe']:
            vrfs = parse_cisco_vrfs(lines, logger)
        elif device_type in ['juniper_mx', 'juniper_srx']:
            vrfs = parse_juniper_vrfs(lines, logger)
        else:
            logger.warning(f"Unsupported device type for VRF parsing: {device_type}")
            
    except Exception as e:
        logger.error(f"VRF parsing failed for {device_type}: {e}")
        # Return empty list on parsing failure
        pass
    
    logger.info(f"Parsed {len(vrfs)} VRFs: {vrfs}")
    return sorted(vrfs)


def parse_huawei_vrfs(lines, logger):
    """Parse Huawei VRF output with enhanced logic for Huawei devices"""
    vrfs = []
    
    # Words that indicate this is a header or non-VRF line
    skip_words = {
        'vpn-instance', 'instance', 'name', 'rd', 'description', 'desc',
        'total', 'count', '----', '====', '*', 'statistics', 'summary',
        'vpn', 'route', 'distinguisher', 'import', 'export', 'target',
        'interface', 'interfaces', 'protocol', 'protocols', 'status'
    }
    
    # Process each line
    for i, line in enumerate(lines):
        original_line = line
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip lines that are clearly headers (contain multiple header keywords)
        line_lower = line.lower()
        header_word_count = sum(1 for word in skip_words if word in line_lower)
        if header_word_count >= 2:  # If line contains 2+ header keywords, it's probably a header
            logger.debug(f"Skipping header line {i} (contains {header_word_count} header words): {line}")
            continue
            
        # Skip separator lines (lines with mostly special characters)
        if len([c for c in line if c in '-=*+|']) > len(line) * 0.5:
            logger.debug(f"Skipping separator line {i}: {line}")
            continue
            
        # Split line into parts
        parts = line.split()
        if not parts:
            continue
            
        # Get the potential VRF name (first word)
        potential_vrf = parts[0]
        
        # Validate the potential VRF name
        if is_valid_vrf_name(potential_vrf, skip_words, logger):
            if potential_vrf not in vrfs:
                logger.info(f"Found Huawei VRF: '{potential_vrf}' from line {i}: {original_line}")
                vrfs.append(potential_vrf)
        else:
            logger.debug(f"Rejected VRF candidate '{potential_vrf}' from line {i}: {line}")
            
    return vrfs


def is_valid_vrf_name(name, skip_words, logger):
    """Validate if a string looks like a valid VRF name"""
    if not name or len(name) == 0:
        return False
        
    name_lower = name.lower()
    
    # Check if it's in our skip words list
    if name_lower in skip_words:
        logger.debug(f"'{name}' is in skip_words list")
        return False
        
    # Don't accept single characters (likely column separators)
    if len(name) <= 1:
        logger.debug(f"'{name}' is too short")
        return False
        
    # Don't accept if it's just numbers
    if name.isdigit():
        logger.debug(f"'{name}' is just digits")
        return False
        
    # Don't accept if it starts with special characters that indicate formatting
    if name.startswith(('-', '=', '*', '+', '|', '[', '(')):
        logger.debug(f"'{name}' starts with special character")
        return False
        
    # VRF names typically contain alphanumeric characters, underscores, hyphens
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        logger.debug(f"'{name}' contains invalid characters for VRF name")
        return False
        
    return True


def parse_cisco_vrfs(lines, logger):
    """Parse Cisco VRF output with enhanced logic"""
    vrfs = []
    
    # Words that indicate this is a header or non-VRF line for Cisco
    skip_words = {
        'name', 'default', 'rd', 'protocols', 'interfaces', 'vrf',
        'total', 'count', '----', '====', '*', 'statistics', 'summary',
        'route', 'distinguisher', 'import', 'export', 'target',
        'protocol', 'interface', 'status', 'state'
    }
    
    # Process each line
    for i, line in enumerate(lines):
        original_line = line
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip lines that are clearly headers (contain multiple header keywords)
        line_lower = line.lower()
        header_word_count = sum(1 for word in skip_words if word in line_lower)
        if header_word_count >= 2:  # If line contains 2+ header keywords, it's probably a header
            logger.debug(f"Skipping Cisco header line {i} (contains {header_word_count} header words): {line}")
            continue
            
        # Skip separator lines (lines with mostly special characters)
        if len([c for c in line if c in '-=*+|']) > len(line) * 0.5:
            logger.debug(f"Skipping Cisco separator line {i}: {line}")
            continue
            
        # Split line into parts
        parts = line.split()
        if not parts:
            continue
            
        # Get the potential VRF name (first word)
        potential_vrf = parts[0]
        
        # Validate the potential VRF name
        if is_valid_vrf_name(potential_vrf, skip_words, logger):
            if potential_vrf not in vrfs:
                logger.info(f"Found Cisco VRF: '{potential_vrf}' from line {i}: {original_line}")
                vrfs.append(potential_vrf)
        else:
            logger.debug(f"Rejected Cisco VRF candidate '{potential_vrf}' from line {i}: {line}")
            
    return vrfs


def parse_juniper_vrfs(lines, logger):
    """Parse Juniper VRF output with enhanced logic"""
    vrfs = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if 'instance-type vrf' in line:
            # Extract VRF name from before "instance-type"
            parts = line.split()
            for j, part in enumerate(parts):
                if part == 'instance-type' and j > 0:
                    potential_vrf = parts[j-1]
                    if potential_vrf not in vrfs:
                        logger.debug(f"Found Juniper VRF: '{potential_vrf}' from line {i}: {line}")
                        vrfs.append(potential_vrf)
                    break
                    
    return vrfs
