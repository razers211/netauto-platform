/**
 * NetAuto Platform JavaScript
 * Provides dynamic form interactions and AJAX functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initializeBootstrapForms();
    initializeTaskStatusPolling();
    initializeFormValidation();
    initializeTooltips();
    initializeConfirmDialogs();
});

/**
 * Add Bootstrap classes to form elements
 */
function initializeBootstrapForms() {
    // Add form-control class to inputs, selects, and textareas
    const formElements = document.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]), select, textarea');
    formElements.forEach(function(element) {
        if (!element.classList.contains('btn') && !element.classList.contains('form-control')) {
            element.classList.add('form-control');
        }
    });

    // Handle checkboxes
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(function(checkbox) {
        checkbox.classList.add('form-check-input');
    });

    // Handle radio buttons
    const radios = document.querySelectorAll('input[type="radio"]');
    radios.forEach(function(radio) {
        radio.classList.add('form-check-input');
    });
}

/**
 * Initialize task status polling for running tasks
 */
function initializeTaskStatusPolling() {
    const taskDetailPage = document.querySelector('[data-task-id]');
    if (taskDetailPage) {
        const taskId = taskDetailPage.dataset.taskId;
        const statusBadge = document.getElementById('status-badge');
        const taskStatus = document.getElementById('task-status');
        
        if (statusBadge && (statusBadge.textContent.includes('Pending') || statusBadge.textContent.includes('Running'))) {
            pollTaskStatus(taskId);
        }
    }
}

/**
 * Poll task status and update UI
 */
function pollTaskStatus(taskId) {
    const interval = setInterval(function() {
        fetch(`/api/tasks/${taskId}/status/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                updateTaskStatus(data);
                
                // Stop polling if task is completed or failed
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(interval);
                    setTimeout(() => location.reload(), 2000); // Reload after 2 seconds
                }
            })
            .catch(error => {
                console.error('Error polling task status:', error);
                clearInterval(interval); // Stop polling on error
            });
    }, 3000); // Poll every 3 seconds
}

/**
 * Update task status in the UI
 */
function updateTaskStatus(data) {
    const statusBadge = document.getElementById('status-badge');
    const taskStatus = document.getElementById('task-status');
    
    if (statusBadge) {
        statusBadge.className = 'badge ' + getBadgeClass(data.status);
        statusBadge.textContent = capitalizeFirst(data.status);
    }
    
    if (taskStatus) {
        taskStatus.className = 'badge ' + getBadgeClass(data.status);
        if (data.status === 'running') {
            taskStatus.classList.add('task-status-running');
        }
        taskStatus.textContent = capitalizeFirst(data.status);
    }
}

/**
 * Get Bootstrap badge class for task status
 */
function getBadgeClass(status) {
    switch (status) {
        case 'completed': return 'bg-success';
        case 'failed': return 'bg-danger';
        case 'running': return 'bg-warning';
        default: return 'bg-secondary';
    }
}

/**
 * Capitalize first letter of string
 */
function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    // IP address validation
    const ipInputs = document.querySelectorAll('input[name*="ip"], input[name*="host"], input[name*="next_hop"]');
    ipInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            validateIPAddress(this);
        });
    });

    // VLAN ID validation
    const vlanInputs = document.querySelectorAll('input[name*="vlan_id"]');
    vlanInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            validateVLANID(this);
        });
    });

    // Interface name validation
    const interfaceInputs = document.querySelectorAll('input[name*="interface"]');
    interfaceInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            validateInterface(this);
        });
    });

    // JSON validation for OSPF networks
    const jsonInputs = document.querySelectorAll('textarea[name*="networks"]');
    jsonInputs.forEach(function(textarea) {
        textarea.addEventListener('blur', function() {
            validateJSON(this);
        });
    });
}

/**
 * Validate IP address format
 */
function validateIPAddress(input) {
    const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    const value = input.value.trim();
    
    if (value && !ipRegex.test(value)) {
        showFieldError(input, 'Please enter a valid IP address (e.g., 192.168.1.1)');
        return false;
    } else {
        clearFieldError(input);
        return true;
    }
}

/**
 * Validate VLAN ID range
 */
function validateVLANID(input) {
    const value = parseInt(input.value);
    
    if (isNaN(value) || value < 1 || value > 4094) {
        showFieldError(input, 'VLAN ID must be between 1 and 4094');
        return false;
    } else {
        clearFieldError(input);
        return true;
    }
}

/**
 * Validate interface name format
 */
function validateInterface(input) {
    const value = input.value.trim();
    const interfaceRegex = /^(GigabitEthernet|FastEthernet|Ethernet|Gi|Fa|Eth|10GE|XGigabitEthernet)\d+([\/\d]+)*$/i;
    
    if (value && !interfaceRegex.test(value)) {
        showFieldError(input, 'Please enter a valid interface name (e.g., GigabitEthernet0/1, Gi0/1, Eth1/1)');
        return false;
    } else {
        clearFieldError(input);
        return true;
    }
}

/**
 * Validate JSON format
 */
function validateJSON(textarea) {
    const value = textarea.value.trim();
    
    if (value) {
        try {
            const parsed = JSON.parse(value);
            if (!Array.isArray(parsed)) {
                throw new Error('JSON must be an array');
            }
            clearFieldError(textarea);
            return true;
        } catch (error) {
            showFieldError(textarea, 'Invalid JSON format. Please check your syntax.');
            return false;
        }
    } else {
        clearFieldError(textarea);
        return true;
    }
}

/**
 * Show field validation error
 */
function showFieldError(input, message) {
    clearFieldError(input); // Clear existing errors first
    
    input.classList.add('is-invalid');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    
    input.parentNode.appendChild(errorDiv);
}

/**
 * Clear field validation error
 */
function clearFieldError(input) {
    input.classList.remove('is-invalid');
    
    const existingError = input.parentNode.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(function(tooltip) {
        new bootstrap.Tooltip(tooltip);
    });
}

/**
 * Initialize confirmation dialogs
 */
function initializeConfirmDialogs() {
    // Delete confirmations
    const deleteButtons = document.querySelectorAll('a[href*="delete"], button[data-action="delete"]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            const confirmMessage = this.dataset.confirm || 'Are you sure you want to delete this item?';
            if (!confirm(confirmMessage)) {
                e.preventDefault();
            }
        });
    });

    // Form submissions that might be destructive
    const forms = document.querySelectorAll('form[data-confirm]');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const confirmMessage = this.dataset.confirm;
            if (!confirm(confirmMessage)) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Show loading spinner on form submission
 */
function showLoadingSpinner(form) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        const originalText = submitButton.innerHTML;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
        submitButton.disabled = true;
        
        // Store original text to restore if needed
        submitButton.dataset.originalText = originalText;
    }
}

/**
 * Hide loading spinner
 */
function hideLoadingSpinner(form) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton && submitButton.dataset.originalText) {
        submitButton.innerHTML = submitButton.dataset.originalText;
        submitButton.disabled = false;
    }
}

/**
 * Auto-refresh page content (for status updates)
 */
function setupAutoRefresh(intervalMs = 30000) {
    const autoRefreshElements = document.querySelectorAll('[data-auto-refresh]');
    
    if (autoRefreshElements.length > 0) {
        setInterval(function() {
            // Only refresh if page is visible
            if (!document.hidden) {
                location.reload();
            }
        }, intervalMs);
    }
}

/**
 * Handle form submissions with loading states
 */
document.addEventListener('submit', function(e) {
    const form = e.target;
    
    // Skip if it's a search form or other non-processing forms
    if (form.classList.contains('no-loading')) {
        return;
    }
    
    // Show loading spinner
    showLoadingSpinner(form);
    
    // Set a timeout to hide spinner in case of slow responses
    setTimeout(function() {
        hideLoadingSpinner(form);
    }, 30000); // 30 seconds timeout
});

/**
 * Dynamic interface configuration form
 */
function initializeInterfaceForm() {
    const modeSelect = document.getElementById('id_mode');
    const accessConfig = document.getElementById('access-config');
    const trunkConfig = document.getElementById('trunk-config');
    const ipConfig = document.getElementById('ip-config');
    
    if (modeSelect && accessConfig && trunkConfig && ipConfig) {
        function toggleConfigSections() {
            const selectedMode = modeSelect.value;
            
            // Hide all sections first
            accessConfig.style.display = 'none';
            trunkConfig.style.display = 'none';
            ipConfig.style.display = 'none';
            
            // Show relevant section
            switch (selectedMode) {
                case 'access':
                    accessConfig.style.display = 'block';
                    break;
                case 'trunk':
                    trunkConfig.style.display = 'block';
                    break;
                case 'ip':
                    ipConfig.style.display = 'block';
                    break;
            }
        }
        
        // Initial toggle
        toggleConfigSections();
        
        // Toggle on change
        modeSelect.addEventListener('change', toggleConfigSections);
    }
}

/**
 * Device quick action shortcuts
 */
function initializeQuickActions() {
    // Add keyboard shortcuts for common actions
    document.addEventListener('keydown', function(e) {
        // Only activate shortcuts when not in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
            return;
        }
        
        // Alt + N: New device
        if (e.altKey && e.key === 'n') {
            e.preventDefault();
            const newDeviceLink = document.querySelector('a[href*="device_create"]');
            if (newDeviceLink) {
                window.location.href = newDeviceLink.href;
            }
        }
        
        // Alt + D: Dashboard
        if (e.altKey && e.key === 'd') {
            e.preventDefault();
            window.location.href = '/';
        }
        
        // Alt + T: Tasks
        if (e.altKey && e.key === 't') {
            e.preventDefault();
            const tasksLink = document.querySelector('a[href*="tasks"]');
            if (tasksLink) {
                window.location.href = tasksLink.href;
            }
        }
    });
}

// Initialize interface form when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeInterfaceForm();
    initializeQuickActions();
});

// Export functions for use in other scripts
window.NetAutoApp = {
    validateIPAddress,
    validateVLANID,
    validateInterface,
    validateJSON,
    showLoadingSpinner,
    hideLoadingSpinner,
    pollTaskStatus,
    updateTaskStatus
};