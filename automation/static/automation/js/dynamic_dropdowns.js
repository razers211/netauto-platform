/**
 * Dynamic dropdown functionality for device interfaces and VRFs
 */

document.addEventListener('DOMContentLoaded', function() {
    const deviceSelect = document.querySelector('select[name="device"]');
    
    if (deviceSelect) {
        deviceSelect.addEventListener('change', function() {
            const deviceId = this.value;
            if (deviceId) {
                loadInterfaces(deviceId);
                loadVRFs(deviceId);
            } else {
                clearDropdowns();
            }
        });
        
        // Load data if device is already selected
        if (deviceSelect.value) {
            loadInterfaces(deviceSelect.value);
            loadVRFs(deviceSelect.value);
        }
    }
});

/**
 * Load interfaces for the selected device
 */
function loadInterfaces(deviceId) {
    const interfaceSelects = document.querySelectorAll('.interface-select');
    
    if (interfaceSelects.length === 0) return;
    
    // Show loading state
    interfaceSelects.forEach(select => {
        select.disabled = true;
        select.innerHTML = '<option value="">Loading interfaces...</option>';
    });
    
    fetch(`/api/devices/${deviceId}/interfaces/`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            interfaceSelects.forEach(select => {
                select.disabled = false;
                select.innerHTML = '<option value="">Select an interface</option>';
                
                if (data.interfaces && data.interfaces.length > 0) {
                    data.interfaces.forEach(interface => {
                        const option = document.createElement('option');
                        option.value = interface;
                        option.textContent = interface;
                        select.appendChild(option);
                    });
                } else {
                    const option = document.createElement('option');
                    option.value = '';
                    option.textContent = 'No interfaces found';
                    select.appendChild(option);
                }
            });
        })
        .catch(error => {
            console.error('Error loading interfaces:', error);
            interfaceSelects.forEach(select => {
                select.disabled = false;
                select.innerHTML = '<option value="">Error loading interfaces</option>';
            });
            
            showNotification('Failed to load interfaces. You can still type the interface name manually.', 'warning');
        });
}

/**
 * Load VRFs for the selected device
 */
function loadVRFs(deviceId) {
    const vrfSelects = document.querySelectorAll('.vrf-select');
    
    if (vrfSelects.length === 0) return;
    
    // Show loading state
    vrfSelects.forEach(select => {
        select.disabled = true;
        select.innerHTML = '<option value="">Loading VRFs...</option>';
    });
    
    fetch(`/api/devices/${deviceId}/vrfs/`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            vrfSelects.forEach(select => {
                select.disabled = false;
                select.innerHTML = '';
                
                // Always add Global (no VRF) option - VRF usage is typically optional
                const globalOption = document.createElement('option');
                globalOption.value = '';
                globalOption.textContent = 'Global (no VRF)';
                select.appendChild(globalOption);
                
                // Add actual VRFs if found
                if (data.vrfs && data.vrfs.length > 0) {
                    data.vrfs.forEach(vrf => {
                        const option = document.createElement('option');
                        option.value = vrf;
                        option.textContent = vrf;
                        select.appendChild(option);
                    });
                }
                
                // Add informational text if no VRFs found
                if (!data.vrfs || data.vrfs.length === 0) {
                    const infoOption = document.createElement('option');
                    infoOption.value = '';
                    infoOption.textContent = '--- No VRFs configured ---';
                    infoOption.disabled = true;
                    infoOption.style.fontStyle = 'italic';
                    select.appendChild(infoOption);
                }
            });
        })
        .catch(error => {
            console.error('Error loading VRFs:', error);
            vrfSelects.forEach(select => {
                select.disabled = false;
                select.innerHTML = '';
                
                // Always provide Global (no VRF) option even on error
                const globalOption = document.createElement('option');
                globalOption.value = '';
                globalOption.textContent = 'Global (no VRF)';
                select.appendChild(globalOption);
                
                // Add error information
                const errorOption = document.createElement('option');
                errorOption.value = '';
                errorOption.textContent = '--- Error loading VRFs ---';
                errorOption.disabled = true;
                errorOption.style.color = 'red';
                errorOption.style.fontStyle = 'italic';
                select.appendChild(errorOption);
            });
            
            showNotification('Failed to load VRFs from device. Global (no VRF) is still available.', 'warning');
        });
}

/**
 * Clear all dropdowns
 */
function clearDropdowns() {
    const interfaceSelects = document.querySelectorAll('.interface-select');
    const vrfSelects = document.querySelectorAll('.vrf-select');
    
    interfaceSelects.forEach(select => {
        select.innerHTML = '<option value="">Select a device first</option>';
        select.disabled = true;
    });
    
    vrfSelects.forEach(select => {
        select.innerHTML = '';
        
        // Always provide Global (no VRF) option
        const globalOption = document.createElement('option');
        globalOption.value = '';
        globalOption.textContent = 'Global (no VRF)';
        select.appendChild(globalOption);
        
        // Add informational option
        const infoOption = document.createElement('option');
        infoOption.value = '';
        infoOption.textContent = '--- Select device to load VRFs ---';
        infoOption.disabled = true;
        infoOption.style.fontStyle = 'italic';
        select.appendChild(infoOption);
        
        select.disabled = false;  // Keep enabled so users can select Global
    });
}

/**
 * Show notification to user
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show mt-3`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert after the first card header or at the top of content
    const target = document.querySelector('.card-header') || document.querySelector('.container-fluid');
    if (target) {
        target.insertAdjacentElement('afterend', notification);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}