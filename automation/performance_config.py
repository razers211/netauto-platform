"""
Performance optimization configuration for network automation tasks.

This module contains settings and utilities for maximizing task execution speed.
"""
import logging

# Performance-focused logging configuration
FAST_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'fast': {
            'format': '%(levelname)s: %(message)s'  # Minimal format for speed
        },
    },
    'handlers': {
        'fast_console': {
            'level': 'INFO',  # Only show important messages
            'class': 'logging.StreamHandler',
            'formatter': 'fast',
        },
    },
    'loggers': {
        'automation.network_automation': {
            'handlers': ['fast_console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Ultra-fast device connection parameters
SPEED_OPTIMIZED_PARAMS = {
    # Connection timeouts (reduced for speed)
    'timeout': 15,           # Reduced from 60s
    'conn_timeout': 8,       # Reduced from 20s  
    'auth_timeout': 10,      # Fast authentication
    'banner_timeout': 8,     # Fast banner detection
    
    # Performance settings
    'fast_cli': True,        # Enable fast CLI mode
    'global_delay_factor': 0.2,  # Very aggressive timing
    'keepalive': 0,          # Disable keepalive for speed
    
    # Disable features that slow down execution
    'auto_connect': True,    # Skip manual connection steps
    'session_timeout': 300,  # Shorter session timeout
}

# Device-specific speed optimizations
DEVICE_SPEED_CONFIGS = {
    'cisco_ios': {
        'global_delay_factor': 0.1,  # Cisco is usually very fast
        'fast_cli': True,
        'timeout': 10,
    },
    'cisco_xe': {
        'global_delay_factor': 0.1,
        'fast_cli': True,
        'timeout': 10,
    },
    'huawei': {
        'global_delay_factor': 0.2,  # Huawei needs slightly more time
        'fast_cli': True,
        'timeout': 12,
    },
    'huawei_vrpv8': {
        'global_delay_factor': 0.2,
        'fast_cli': True,
        'timeout': 12,
    },
}

def apply_speed_optimizations(device_params: dict) -> dict:
    """
    Apply speed optimizations to device parameters.
    
    Args:
        device_params: Original device connection parameters
        
    Returns:
        Optimized device parameters for maximum speed
    """
    # Start with speed-optimized base settings
    optimized = device_params.copy()
    optimized.update(SPEED_OPTIMIZED_PARAMS)
    
    # Apply device-specific optimizations
    device_type = device_params.get('device_type', '')
    if device_type in DEVICE_SPEED_CONFIGS:
        optimized.update(DEVICE_SPEED_CONFIGS[device_type])
    
    # Performance flags
    optimized['debug_mode'] = False  # Disable debugging for speed
    optimized['auto_save'] = True    # Keep auto-save for safety
    optimized['auto_commit'] = True  # Keep auto-commit for Huawei
    
    return optimized

def configure_fast_logging():
    """Configure logging for maximum performance."""
    import logging.config
    logging.config.dictConfig(FAST_LOGGING_CONFIG)

# Command execution performance settings
FAST_COMMAND_SETTINGS = {
    'cisco': {
        'delay_factor': 0.1,
        'max_loops': 20,
        'strip_prompt': True,
        'strip_command': True,
    },
    'huawei': {
        'delay_factor': 0.2,
        'max_loops': 30,
        'strip_prompt': True,
        'strip_command': True,
    },
    'generic': {
        'delay_factor': 0.3,
        'max_loops': 25,
        'strip_prompt': True,
        'strip_command': True,
    }
}

def get_fast_command_settings(device_type: str) -> dict:
    """Get optimized command execution settings for device type."""
    for key, settings in FAST_COMMAND_SETTINGS.items():
        if key in device_type.lower():
            return settings
    return FAST_COMMAND_SETTINGS['generic']