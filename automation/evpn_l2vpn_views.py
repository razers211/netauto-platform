from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
import threading

from .models import Device, NetworkTask
from .forms import (
    DeviceSelectionForm, L2VPWSForm, L2VPNSVCForm, EVPNInstanceForm, BridgeDomainForm
)
from .evpn_l2vpn import EVPNManager

def execute_task_async(task):
    from .views import execute_network_task
    success, result, error = execute_network_task(
        task.device.get_connection_params(),
        task.task_type,
        task.parameters
    )
    # Mark task completed/failed
    from .views import NetworkAutomationError
    try:
        if success:
            task.status = 'completed'
            task.result = result
        else:
            task.status = 'failed'
            task.error_message = error
        task.save()
    except Exception:
        task.status = 'failed'
        task.save()

@login_required
def l2vpws(request):
    """Configure L2VPWS on selected device"""
    if request.method == 'POST':
        form = L2VPWSForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            task = NetworkTask.objects.create(
                device=device,
                task_type='l2vpws',
                parameters={
                    'service_name': form.cleaned_data['service_name'],
                    'local_if': form.cleaned_data['local_if'],
                    'remote_ip': form.cleaned_data['remote_ip'],
                    'vc_id': form.cleaned_data['vc_id'],
                    'description': form.cleaned_data.get('description')
                },
                created_by=request.user
            )
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            messages.success(request, f'L2VPWS task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = L2VPWSForm()
        device_form = DeviceSelectionForm()
    context = {'form': form, 'device_form': device_form, 'title': 'Configure L2VPWS'}
    return render(request, 'automation/l2vpws_form.html', context)

@login_required
def l2vpn_vpls(request):
    """Configure L2VPN VPLS on selected device"""
    if request.method == 'POST':
        form = L2VPNSVCForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            task = NetworkTask.objects.create(
                device=device,
                task_type='l2vpn_vpls',
                parameters={
                    'service_name': form.cleaned_data['service_name'],
                    'vpls_id': form.cleaned_data['vpls_id'],
                    'rd': form.cleaned_data.get('rd'),
                    'rt_both': form.cleaned_data.get('rt_both'),
                    'description': form.cleaned_data.get('description')
                },
                created_by=request.user
            )
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            messages.success(request, f'VPLS task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = L2VPNSVCForm()
        device_form = DeviceSelectionForm()
    context = {'form': form, 'device_form': device_form, 'title': 'Configure L2VPN VPLS'}
    return render(request, 'automation/l2vpn_vpls_form.html', context)

@login_required
def evpn_instance(request):
    """Configure EVPN Instance (VPLS) on selected device"""
    if request.method == 'POST':
        form = EVPNInstanceForm(request.POST)
        device_form = DeviceSelectionForm(request.POST)
        if form.is_valid() and device_form.is_valid():
            device = device_form.cleaned_data['device']
            task = NetworkTask.objects.create(
                device=device,
                task_type='evpn_instance',
                parameters={
                    'instance_name': form.cleaned_data['instance_name'],
                    'vpls_id': form.cleaned_data['vpls_id'],
                    'rd': form.cleaned_data.get('rd'),
                    'route_target': form.cleaned_data.get('rt_target'),
                    'route_target_id': form.cleaned_data.get('rt_id'),
                    'encapsulation': form.cleaned_data.get('encapsulation', 'mpls'),
                    'replication_type': form.cleaned_data.get('replication_type', 'ingress'),
                    'description': form.cleaned_data.get('description')
                },
                created_by=request.user
            )
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            messages.success(request, f'EVPN Instance task submitted for {device.name}')
            return redirect('task_detail', task_id=task.id)
    else:
        form = EVPNInstanceForm()
        device_form = DeviceSelectionForm()
    context = {'form': form, 'device_form': device_form, 'title': 'Configure EVPN Instance'}
    return render(request, 'automation/evpn_instance_form.html', context)

@login_required
def bridge_domain(request):
    """Add Bridge Domain to EVPN Instance"""
    if request.method == 'POST':
        form = BridgeDomainForm(request.POST)
        if form.is_valid():
            task = NetworkTask.objects.create(
                device=form.cleaned_data['device'],
                task_type='bridge_domain',
                parameters={
                    'instance_name': form.cleaned_data['instance_name'],
                    'bd_name': form.cleaned_data['bd_name'],
                    'vlan_id': form.cleaned_data['vlan_id'],
                    'interface': form.cleaned_data.get('interface'),
                    'description': form.cleaned_data.get('description')
                },
                created_by=request.user
            )
            thread = threading.Thread(target=execute_task_async, args=(task,))
            thread.start()
            messages.success(request, 'Bridge Domain task submitted')
            return redirect('task_detail', task_id=task.id)
    else:
        form = BridgeDomainForm()
    context = {'form': form, 'title': 'Add Bridge Domain to EVPN'}
    return render(request, 'automation/bridge_domain_form.html', context)