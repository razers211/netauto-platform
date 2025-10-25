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
                const isRequired = !select.hasAttribute('data-allow-empty');
                
                select.disabled = false;
                select.innerHTML = '';
                
                // Add empty option for optional VRF fields
                if (!isRequired) {
                    const emptyOption = document.createElement('option');
                    emptyOption.value = '';
                    emptyOption.textContent = 'Global (no VRF)';
                    select.appendChild(emptyOption);
                }
                
                if (data.vrfs && data.vrfs.length > 0) {
                    data.vrfs.forEach(vrf => {
                        const option = document.createElement('option');
                        option.value = vrf;
                        option.textContent = vrf;
                        select.appendChild(option);
                    });
                } else if (isRequired) {
                    const option = document.createElement('option');
                    option.value = '';
                    option.textContent = 'No VRFs found';
                    select.appendChild(option);
                }
            });
        })
        .catch(error => {
            console.error('Error loading VRFs:', error);
            vrfSelects.forEach(select => {
                const isRequired = !select.hasAttribute('data-allow-empty');
                
                select.disabled = false;
                select.innerHTML = '';
                
                if (!isRequired) {
                    const emptyOption = document.createElement('option');
                    emptyOption.value = '';
                    emptyOption.textContent = 'Global (no VRF)';
                    select.appendChild(emptyOption);
                }
                
                const errorOption = document.createElement('option');
                errorOption.value = '';
                errorOption.textContent = 'Error loading VRFs';
                select.appendChild(errorOption);
            });
            
            showNotification('Failed to load VRFs. You can still select Global or manually configure VRFs first.', 'warning');
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
        const isRequired = !select.hasAttribute('data-allow-empty');
        select.innerHTML = '';
        
        if (!isRequired) {
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = 'Select a device first';
            select.appendChild(emptyOption);
        } else {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'Select a device first';
            select.appendChild(option);
        }
        
        select.disabled = true;
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