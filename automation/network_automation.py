"""
Network automation scripts using Netmiko for Cisco and Huawei devices; PyEZ for Juniper.
"""

import time
import logging
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from typing import Dict, List, Optional, Tuple
import re
from functools import wraps
try:
    from .juniper_manager import JuniperDeviceManager
except ImportError:
    JuniperDeviceManager = None

try:
    from .evpn_l2vpn import EVPNManager as JuniperEVPNManager
except ImportError:
    JuniperEVPNManager = None

logger = logging.getLogger(__name__)


def performance_monitor(operation_name):
    """Decorator to monitor operation performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"⚡ {operation_name} completed in {duration:.2f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"❌ {operation_name} failed after {duration:.2f}s: {e}")
                raise
        return wrapper
    return decorator


class NetworkAutomationError(Exception):
    """Custom exception for network automation errors."""
    pass


class NetworkDeviceManager:
    """
    Manager class for network device operations using Netmiko or PyEZ.
    Supports Cisco, Huawei, and Juniper devices.
    """
    
    def __init__(self, device_params: Dict):
        self.device_params = device_params
        self.connection = None
        self.device_type = device_params.get('device_type', '')
        
        # Select backend driver
        if self.device_type and ('juniper' in self.device_type) and JuniperDeviceManager:
            self.driver = JuniperDeviceManager(device_params)
        else:
            self.driver = None
        # Enhance connection parameters for better reliability
        self._enhance_connection_params()
    
    def _enhance_connection_params(self):
        """Enhance connection parameters for optimal performance and reliability"""
        # Aggressive performance optimizations
        self.device_params.setdefault('timeout', 20)  # Reduced from 60s
        self.device_params.setdefault('conn_timeout', 10)  # Fast connection timeout
        
        # Performance-focused settings
        self.device_params.setdefault('fast_cli', True)  # Enable fast CLI mode
        self.device_params.setdefault('global_delay_factor', 0.5)  # Much faster delays
        
        # Disable session logging for performance (only enable for debugging)
        if not self.device_params.get('debug_mode', False):
            self.device_params.pop('session_log', None)
        
        # Device-specific performance optimizations (balanced for reliability)
        if 'huawei' in self.device_type:
            # Huawei optimizations - prioritize reliability over speed
            self.device_params.setdefault('global_delay_factor', 1.0)
            self.device_params['fast_cli'] = False  # Disable fast_cli for Huawei to reduce prompt issues
            
            # Configure enable mode credentials
            if 'secret' not in self.device_params and 'enable_password' not in self.device_params:
                if 'password' in self.device_params:
                    self.device_params['secret'] = self.device_params['password']
        
        elif 'cisco' in self.device_type:
            # Cisco optimizations - balanced speed and reliability
            self.device_params.setdefault('global_delay_factor', 0.5)  # More conservative for Cisco
            self.device_params.setdefault('fast_cli', True)
    
    # Removed slow testing methods - replaced with fast session setup
        
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        
    @performance_monitor("Device Connection")
    def connect(self) -> bool:
        """Establish connection to network device with optimized setup"""
        if self.driver:
            return self.driver.connect()
        # Original Netmiko path
        try:
            logger.debug(f"Connecting to {self.device_params['host']}...")
            
            self.connection = ConnectHandler(**self.device_params)
            logger.debug(f"Socket connected to {self.device_params['host']}")
            
            # Fast session setup - skip extensive testing in favor of speed
            self._fast_session_setup()
            
            return True
            
        except NetmikoTimeoutException as e:
            logger.error(f"Connection timeout to {self.device_params['host']}: {e}")
            raise NetworkAutomationError(f"Connection timeout: {e}")
        except NetmikoAuthenticationException as e:
            logger.error(f"Authentication failed for {self.device_params['host']}: {e}")
            raise NetworkAutomationError(f"Authentication failed: {e}")
        except Exception as e:
            logger.error(f"Connection failed to {self.device_params['host']}: {e}")
            raise NetworkAutomationError(f"Connection failed: {e}")
    
    def _fast_session_setup(self):
        """Minimal session setup for maximum speed"""
        try:
            # Get initial prompt quickly
            self.connection.find_prompt()
            
            # Set essential session parameters only
            if 'cisco' in self.device_type:
                self.connection.send_command("terminal length 0", delay_factor=0.1)
            elif 'huawei' in self.device_type:
                self.connection.send_command("screen-length 0 temporary", delay_factor=0.1)
                
            logger.debug("Fast session setup completed")
        except Exception as e:
            logger.debug(f"Fast session setup failed (continuing anyway): {e}")
    
    def disconnect(self):
        """Close connection to network device."""
        if self.driver:
            self.driver.disconnect()
        elif self.connection:
            self.connection.disconnect()
            logger.info(f"Disconnected from {self.device_params['host']}")
    
    def execute_command(self, command: str, use_textfsm: bool = False) -> str:
        """Execute command with optimized performance settings"""
        if self.driver:
            return self.driver.execute_command(command)
        # Original Netmiko path
        if not self.connection:
            raise NetworkAutomationError("Not connected to device")
        
        logger.debug(f"Executing: {command}")
        start_time = time.time()
        
        try:
            # Fast command execution with minimal overhead
            if 'huawei' in self.device_type:
                output = self.connection.send_command(
                    command, 
                    use_textfsm=use_textfsm,
                    delay_factor=0.8,  # Increased for better prompt detection
                    max_loops=100,  # Increased for reliability
                    strip_prompt=True,
                    strip_command=True
                )
            elif 'cisco' in self.device_type:
                output = self.connection.send_command(
                    command,
                    use_textfsm=use_textfsm,
                    delay_factor=0.5,  # Increased for better prompt detection
                    max_loops=80,   # Increased for reliability
                    strip_prompt=True,
                    strip_command=True
                )
            else:
                # Default balanced settings
                output = self.connection.send_command(
                    command,
                    use_textfsm=use_textfsm,
                    delay_factor=1.0,  # Conservative for unknown devices
                    max_loops=100,
                    strip_prompt=True,
                    strip_command=True
                )
            
            exec_time = time.time() - start_time
            output_length = len(output) if output else 0
            logger.debug(f"Command completed in {exec_time:.2f}s - {output_length} chars")
            
            return output if output else "No output received from device"
            
        except Exception as e:
            exec_time = time.time() - start_time
            logger.error(f"Command '{command}' failed after {exec_time:.2f}s: {e}")
            raise NetworkAutomationError(f"Command failed: {e}")
    
    def _check_connection_health(self) -> bool:
        """Fast connection health check using minimal operations"""
        if not self.connection:
            return False
            
        try:
            # Quick connection object check
            if not hasattr(self.connection, 'remote_conn') or not self.connection.remote_conn:
                return False
            
            # Fast prompt check - this is usually sufficient
            prompt = self.connection.find_prompt()
            return bool(prompt and len(prompt.strip()) > 0)
                
        except Exception:
            return False
    
    def _reconnect_if_needed(self) -> bool:
        """Check if connection is alive and reconnect if needed with multiple attempts."""
        max_reconnect_attempts = 3
        
        # First check if we're actually disconnected
        if self._check_connection_health():
            logger.debug("Connection is healthy, no reconnection needed")
            return True
        
        logger.warning("Connection health check failed. Attempting to reconnect...")
        
        for attempt in range(max_reconnect_attempts):
            try:
                # Clean up existing connection
                if self.connection:
                    try:
                        self.connection.disconnect()
                    except:
                        pass
                    self.connection = None
                
                # Wait a bit before reconnecting (especially on retries)
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                    logger.info(f"Waiting {wait_time}s before reconnection attempt {attempt + 1}")
                    time.sleep(wait_time)
                
                # Attempt to reconnect
                logger.info(f"Reconnection attempt {attempt + 1}/{max_reconnect_attempts} to {self.device_params['host']}")
                self.connection = ConnectHandler(**self.device_params)
                
                # Verify the new connection works
                if self._check_connection_health():
                    logger.info(f"Successfully reconnected to {self.device_params['host']} on attempt {attempt + 1}")
                    # Re-setup the session
                    self._fast_session_setup()
                    return True
                else:
                    logger.warning(f"Reconnection attempt {attempt + 1} succeeded but health check failed")
                    
            except Exception as reconnect_error:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {reconnect_error}")
                if attempt == max_reconnect_attempts - 1:
                    logger.error(f"All {max_reconnect_attempts} reconnection attempts failed")
                    raise NetworkAutomationError(f"Connection lost and reconnection failed after {max_reconnect_attempts} attempts: {reconnect_error}")
        
        return False
    
    def execute_config_commands(self, commands: List[str]) -> str:
        """Execute configuration commands on the device with connection recovery."""
        if self.driver:
            return self.driver.execute_config_commands(commands)
        # Original Netmiko path
        if not self.connection:
            raise NetworkAutomationError("Not connected to device")
        
        device_type = self.device_params.get('device_type', '')
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                # Check and restore connection if needed
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt} for configuration commands")
                    self._reconnect_if_needed()
                
                return self._execute_config_commands_internal(commands, device_type)
                
            except Exception as e:
                error_str = str(e).lower()
                if ('socket is closed' in error_str or 'connection' in error_str or 
                    'broken pipe' in error_str or 'timeout' in error_str) and attempt < max_retries:
                    logger.warning(f"Connection error on attempt {attempt + 1}: {e}. Retrying...")
                    time.sleep(2)  # Brief pause before retry
                    continue
                else:
                    # Final attempt failed or non-connection error
                    logger.error(f"Configuration failed after {attempt + 1} attempts: {e}")
                    raise NetworkAutomationError(f"Configuration failed: {e}")
    
    def _execute_config_commands_internal(self, commands: List[str], device_type: str) -> str:
        """Internal method to execute configuration commands using Netmiko built-in methods"""
        
        if 'cisco' in device_type:
            return self._execute_cisco_config(commands)
        elif 'huawei' in device_type:
            return self._execute_huawei_config(commands)
        else:
            return self._execute_generic_config(commands)
    
    @performance_monitor("Cisco Configuration")
    def _execute_cisco_config(self, commands: List[str]) -> str:
        """Execute Cisco configuration with optimized speed"""
        logger.info(f"Configuring Cisco device with {len(commands)} commands")
        
        try:
            # Ensure we're in enable mode first
            if not self.connection.check_enable_mode():
                logger.debug("Entering Cisco enable mode")
                self.connection.enable()
                enable_prompt = self.connection.find_prompt()
                logger.debug(f"Enable mode prompt: '{enable_prompt}'")
            
            # High-speed configuration execution with proper mode handling
            logger.debug("Executing Cisco configuration commands")
            config_output = self.connection.send_config_set(
                commands, 
                delay_factor=0.5,  # Increased from 0.2 for better prompt detection
                cmd_verify=False,   # Skip verification for speed
                enter_config_mode=True,   # Let Netmiko handle config mode
                exit_config_mode=True     # Let Netmiko handle exit
            )
            
            # Fast save (optional - can be disabled for even more speed)
            if self.device_params.get('auto_save', True):
                save_output = self.connection.save_config()
                result = config_output + "\n\n--- SAVE OUTPUT ---\n" + save_output
            else:
                result = config_output + "\n\n--- SAVE SKIPPED FOR SPEED ---"
            
            return result
            
        except Exception as e:
            logger.error(f"Cisco configuration failed: {e}")
            raise NetworkAutomationError(f"Cisco configuration failed: {e}")
    
    @performance_monitor("Huawei Configuration")
    def _execute_huawei_config(self, commands: List[str]) -> str:
        """Execute Huawei configuration with maximum speed optimizations"""
        logger.info(f"Configuring Huawei device with {len(commands)} commands")
        
        try:
            # Try fast manual config mode first
            try:
                self._fast_enter_huawei_config()
                
                # Execute with manual interactive handling to auto-ack Y/N prompts
                logger.debug(f"Sending {len(commands)} commands with interactive handling")
                config_output = self._send_huawei_interactive_commands(commands)
                
                self._fast_exit_huawei_config()
                
            except Exception as manual_error:
                logger.warning(f"Manual config mode failed: {manual_error}")
                logger.info("Falling back to Netmiko automatic mode handling")
                
                # Fallback to Netmiko's built-in mode handling
                config_output = self.connection.send_config_set(
                    commands,
                    delay_factor=0.5,  # Slightly slower but more reliable
                    cmd_verify=False,
                    enter_config_mode=True,   # Let Netmiko handle it
                    exit_config_mode=True     # Let Netmiko handle it
                )
            
            logger.debug(f"Configuration output length: {len(config_output)}")
            
            # Fast commit and save (simplified)
            if self.device_params.get('auto_commit', True):
                commit_save_output = self._fast_huawei_commit_save()
                result = config_output + "\n\n" + commit_save_output
            else:
                result = config_output + "\n\n--- COMMIT/SAVE SKIPPED FOR SPEED ---"
            
            return result
            
        except Exception as e:
            logger.error(f"Huawei configuration failed: {e}")
            
            # Emergency exit from config mode
            try:
                self.connection.send_command("quit", delay_factor=0.1)
            except:
                pass
                
            raise NetworkAutomationError(f"Huawei configuration failed: {e}")
    
    def _fast_enter_huawei_config(self):
        """Fast entry to Huawei system-view configuration mode with interactive prompt handling"""
        try:
            # Check current prompt to see if already in system-view
            current_prompt = self.connection.find_prompt()
            logger.debug(f"Current Huawei prompt: '{current_prompt}'")
            
            # If already in system-view (prompt ends with ]), skip entry
            if current_prompt.strip().endswith(']'):
                logger.debug("Already in Huawei system-view")
                return
            
            # Enter system-view mode (handle potential interactive [Y/N] prompts)
            logger.debug("Entering Huawei system-view...")
            result = self.connection.send_command_timing(
                "system-view",
                strip_prompt=False,
                strip_command=False
            )
            
            # Handle confirmation prompts generically
            lower_res = (result or "").lower()
            if any(k in lower_res for k in ["[y/n]", " y/n ", "please choose 'yes' or 'no'", "confirm", "are you sure"]):
                logger.debug("Detected confirmation prompt on system-view entry; sending 'Y'")
                result += self.connection.send_command_timing("Y", strip_prompt=False, strip_command=False)
            
            # Verify entry was successful
            new_prompt = self.connection.find_prompt()
            logger.debug(f"After system-view prompt: '{new_prompt}'")
            
            # Check for errors in command output
            if any(err in (result or "") for err in ["Error", "Unrecognized", "Invalid"]):
                raise NetworkAutomationError(f"System-view command failed: {result[:200]}")
                
            # Verify we're in config mode (prompt should end with ] for Huawei)
            if not new_prompt.strip().endswith(']'):
                logger.warning(f"System-view verification failed. Expected ']' prompt, got: '{new_prompt}'")
                # Still continue - some Huawei devices may have different prompt patterns
                
        except Exception as e:
            logger.error(f"Cannot enter Huawei system-view: {e}")
            raise NetworkAutomationError(f"Cannot enter Huawei config mode: {e}")
    
    def _fast_exit_huawei_config(self):
        """Fast exit from Huawei system-view configuration mode with interactive prompt handling"""
        try:
            # Check current prompt
            current_prompt = self.connection.find_prompt()
            logger.debug(f"Before exit prompt: '{current_prompt}'")
            
            # If not in system-view (doesn't end with ]), already out
            if not current_prompt.strip().endswith(']'):
                logger.debug("Not in Huawei system-view, no need to exit")
                return
            
            # Exit system-view with quit command (handle possible confirmation prompts)
            logger.debug("Exiting Huawei system-view...")
            result = self.connection.send_command_timing(
                "quit",
                strip_prompt=False,
                strip_command=False
            )
            
            lower_res = (result or "").lower()
            if any(k in lower_res for k in ["[y/n]", " y/n ", "please choose 'yes' or 'no'", "confirm", "are you sure"]):
                # Prefer to confirm exit so we don't get stuck
                logger.debug("Detected confirmation prompt on exit; sending 'Y'")
                result += self.connection.send_command_timing("Y", strip_prompt=False, strip_command=False)
            
            # Verify exit
            new_prompt = self.connection.find_prompt()
            logger.debug(f"After quit prompt: '{new_prompt}'")
            
            # Prefer '>' but accept other non-config prompts as success
            if new_prompt.strip().endswith(('>', '#')):
                logger.debug("Successfully exited to operational view")
            else:
                logger.warning(f"Exit may not have worked. Prompt: '{new_prompt}'")
                
        except Exception as e:
            logger.warning(f"Exit from Huawei system-view failed: {e}")
    
    def _fast_huawei_commit_save(self) -> str:
        """Fast commit and save for Huawei devices with timing-based prompt handling"""
        results = []
        
        try:
            # Fast commit
            if hasattr(self.connection, 'commit'):
                # Try Netmiko's commit if available
                commit_result = self.connection.commit()
                results.append(f"--- FAST COMMIT ---\n{commit_result}")
            else:
                # Manual fast commit using timing to handle Y/N
                commit_out = self.connection.send_command_timing("commit", strip_prompt=False, strip_command=False)
                if any(tok in (commit_out or '').lower() for tok in ['[y/n]', ' y/n ', 'confirm', 'are you sure']):
                    commit_out += self.connection.send_command_timing("Y", strip_prompt=False, strip_command=False)
                results.append(f"--- FAST COMMIT ---\n{commit_out}")
        except Exception as e:
            # Attempt one reconnect and retry commit once
            try:
                self._reconnect_if_needed()
                self._fast_enter_huawei_config()
                commit_out = self.connection.send_command_timing("commit", strip_prompt=False, strip_command=False)
                if any(tok in (commit_out or '').lower() for tok in ['[y/n]', ' y/n ', 'confirm', 'are you sure']):
                    commit_out += self.connection.send_command_timing("Y", strip_prompt=False, strip_command=False)
                results.append(f"--- FAST COMMIT (RETRY) ---\n{commit_out}")
            except Exception as e2:
                results.append(f"--- COMMIT FAILED ---\n{e2}")
        
        try:
            # Fast save using timing to avoid strict expect patterns
            save_out = self.connection.send_command_timing("save", strip_prompt=False, strip_command=False)
            if any(tok in (save_out or '').lower() for tok in ['[y/n]', ' y/n ', 'overwrite', 'confirm']):
                save_out += self.connection.send_command_timing("Y", strip_prompt=False, strip_command=False)
            results.append(f"--- FAST SAVE ---\n{save_out}")
        except Exception as e:
            # Attempt one reconnect and retry save once
            try:
                self._reconnect_if_needed()
                self._fast_enter_huawei_config()
                save_out = self.connection.send_command_timing("save", strip_prompt=False, strip_command=False)
                if any(tok in (save_out or '').lower() for tok in ['[y/n]', ' y/n ', 'overwrite', 'confirm']):
                    save_out += self.connection.send_command_timing("Y", strip_prompt=False, strip_command=False)
                results.append(f"--- FAST SAVE (RETRY) ---\n{save_out}")
            except Exception as e2:
                results.append(f"--- SAVE FAILED ---\n{e2}")
        
        return "\n\n".join(results)
    
    def debug_connection_state(self) -> dict:
        """Debug method to check connection and prompt state"""
        if self.driver:
            return {'driver': 'Juniper', 'connected': bool(self.driver.juniper_dev.dev), 'host': self.device_params.get('host', 'unknown')}
        # Original Netmiko path
        debug_info = {}
        
        try:
            # Basic connection info
            debug_info['connected'] = bool(self.connection and self.connection.remote_conn)
            debug_info['device_type'] = self.device_type
            debug_info['host'] = self.device_params.get('host', 'unknown')
            
            if self.connection:
                # Get current prompt with generous timing
                try:
                    current_prompt = self.connection.find_prompt(delay_factor=2.0)
                    debug_info['current_prompt'] = current_prompt
                    debug_info['prompt_length'] = len(current_prompt)
                    debug_info['prompt_ends_with'] = current_prompt[-5:] if len(current_prompt) >= 5 else current_prompt
                except Exception as prompt_error:
                    debug_info['prompt_error'] = str(prompt_error)
                
                # Test simple command
                try:
                    test_cmd = "display clock" if 'huawei' in self.device_type else "show clock"
                    test_output = self.connection.send_command(test_cmd, delay_factor=2.0, max_loops=200)
                    debug_info['test_command'] = test_cmd
                    debug_info['test_output_length'] = len(test_output) if test_output else 0
                    debug_info['test_success'] = len(test_output) > 10 if test_output else False
                except Exception as test_error:
                    debug_info['test_error'] = str(test_error)
                    
            else:
                debug_info['connection_object'] = 'None'
                
        except Exception as e:
            debug_info['debug_error'] = str(e)
        
        return debug_info
    
    def _enter_huawei_config_mode(self) -> bool:
        """Enter Huawei configuration mode using best available method"""
        try:
            # Method 1: Try Netmiko's enable() method first
            if hasattr(self.connection, 'check_enable_mode') and hasattr(self.connection, 'enable'):
                try:
                    if not self.connection.check_enable_mode():
                        logger.info("Attempting Netmiko enable() for Huawei")
                        self.connection.enable()
                    
                    if self.connection.check_enable_mode():
                        enable_prompt = self.connection.find_prompt()
                        logger.info(f"Huawei enable mode successful - prompt: '{enable_prompt}'")
                        return True
                        
                except Exception as enable_error:
                    logger.info(f"Netmiko enable() not supported for this Huawei device: {enable_error}")
            
            # Method 2: Fallback to manual system-view
            logger.info("Attempting manual system-view entry")
            result = self.connection.send_command("system-view", delay_factor=2)
            
            if "Error" not in result and "Unrecognized" not in result:
                system_prompt = self.connection.find_prompt()
                logger.info(f"Huawei system-view successful - prompt: '{system_prompt}'")
                return True
            else:
                logger.warning(f"System-view returned: {result[:100]}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to enter Huawei config mode: {e}")
            return False
    
    def _exit_huawei_config_mode(self):
        """Exit Huawei configuration mode properly"""
        try:
            # Try Netmiko's exit_config_mode first
            if hasattr(self.connection, 'exit_config_mode'):
                try:
                    self.connection.exit_config_mode()
                    exit_prompt = self.connection.find_prompt()
                    logger.info(f"Exited config mode via Netmiko - prompt: '{exit_prompt}'")
                    return
                except Exception as exit_error:
                    logger.info(f"Netmiko exit_config_mode failed: {exit_error}")
            
            # Fallback to manual quit
            self.connection.send_command("quit")
            quit_prompt = self.connection.find_prompt()
            logger.info(f"Exited config mode via quit - prompt: '{quit_prompt}'")
            
        except Exception as e:
            logger.warning(f"Could not exit config mode cleanly: {e}")
    
    @performance_monitor("Generic Configuration")
    def _execute_generic_config(self, commands: List[str]) -> str:
        """Execute configuration for generic/other device types"""
        logger.info(f"Configuring generic device with {len(commands)} commands")
        
        try:
            # Use Netmiko's built-in config mode handling for reliability
            config_output = self.connection.send_config_set(
                commands,
                delay_factor=0.3,
                cmd_verify=False,
                enter_config_mode=True,  # Let Netmiko handle mode entry
                exit_config_mode=True    # Let Netmiko handle mode exit
            )
            
            # Try to save if available
            if self.device_params.get('auto_save', True):
                try:
                    save_output = self.connection.save_config()
                    return config_output + "\n\n--- SAVE OUTPUT ---\n" + save_output
                except Exception:
                    logger.info("save_config() not available for this device type")
                    return config_output + "\n\n--- SAVE NOT AVAILABLE ---"
            else:
                return config_output + "\n\n--- SAVE SKIPPED FOR SPEED ---"
                
        except Exception as e:
            logger.error(f"Generic configuration failed: {e}")
            raise NetworkAutomationError(f"Configuration failed: {e}")
    
    def _execute_commands_individually(self, commands: List[str], device_type: str) -> str:
        """Fallback method to execute commands individually when send_config_set fails."""
        config_output = ""
        
        try:
            # Try to enter system-view manually
            self.connection.send_command("system-view")
        except Exception as e:
            logger.warning(f"Could not enter system-view manually: {e}")
        
        # Process commands individually
        for command in commands:
            try:
                cmd_output = self.connection.send_command(command, delay_factor=2)
                config_output += f"{command}: {cmd_output}\n"
            except Exception as e:
                logger.warning(f"Command '{command}' failed: {e}")
                config_output += f"{command}: ERROR - {e}\n"
        
        # Try to exit configuration mode
        try:
            self.connection.send_command("quit")
        except Exception:
            pass
        
        return config_output

    def _send_huawei_interactive_commands(self, commands: List[str]) -> str:
        """Send Huawei config commands using timing API with auto-confirm and resilience."""
        outputs = []
        confirmation_tokens = ["[y/n]", " y/n ", "please choose 'yes' or 'no'", "continue?", "are you sure", "confirm"]
        for idx, cmd in enumerate(commands):
            try:
                out = self.connection.send_command_timing(cmd, strip_prompt=False, strip_command=False)
            except Exception as e:
                # Attempt reconnection once if socket closed
                if 'socket is closed' in str(e).lower() or 'timed out' in str(e).lower():
                    try:
                        self._reconnect_if_needed()
                        self._fast_enter_huawei_config()
                        out = self.connection.send_command_timing(cmd, strip_prompt=False, strip_command=False)
                    except Exception as e2:
                        raise e2
                else:
                    raise
            
            # Handle one or more confirmation prompts in sequence
            loop_guard = 0
            last_chunk = out
            while last_chunk and any(tok in last_chunk.lower() for tok in confirmation_tokens) and loop_guard < 3:
                last_chunk = self.connection.send_command_timing("Y", strip_prompt=False, strip_command=False)
                out = (out or "") + last_chunk
                loop_guard += 1
            
            # Small pacing to keep session stable (more after context switches)
            try:
                if cmd.startswith(('ospf', 'bgp', 'interface', 'l2vpn-family', 'ipv4-family')):
                    time.sleep(0.2)
                else:
                    time.sleep(0.05)
            except Exception:
                pass
            
            outputs.append(f"$ {cmd}\n{out}" if out is not None else f"$ {cmd}\n")
        return "\n".join(outputs)
    
    def _huawei_commit_and_save_enhanced(self) -> str:
        """Enhanced Huawei commit and save using Netmiko built-in methods where possible"""
        output_parts = []
        
        # Try Netmiko's commit method first (if available)
        commit_success = self._try_netmiko_commit()
        if commit_success:
            output_parts.append("--- COMMIT OUTPUT ---\nConfiguration committed successfully via Netmiko")
        else:
            # Fallback to manual commit handling
            commit_output = self._manual_huawei_commit()
            output_parts.append(f"--- COMMIT OUTPUT ---\n{commit_output}")
        
        # Handle save operation
        save_output = self._huawei_save_config()
        output_parts.append(f"--- SAVE OUTPUT ---\n{save_output}")
        
        return "\n\n".join(output_parts)
    
    def _try_netmiko_commit(self) -> bool:
        """Try to use Netmiko's built-in commit method for Huawei"""
        try:
            if hasattr(self.connection, 'commit'):
                logger.info("Attempting Huawei commit using Netmiko's built-in method")
                
                # Some versions of Netmiko have a commit() method for Huawei devices
                result = self.connection.commit()
                
                if result and "error" not in result.lower():
                    logger.info("Netmiko commit() successful")
                    return True
                else:
                    logger.info(f"Netmiko commit() returned: {result}")
                    return False
            else:
                logger.debug("Netmiko commit() method not available")
                return False
                
        except Exception as e:
            logger.info(f"Netmiko commit() failed: {e}")
            return False
    
    def _manual_huawei_commit(self) -> str:
        """Manual Huawei commit handling with improved prompt detection"""
        try:
            logger.info("Performing manual Huawei commit...")
            
            # Get current prompt before commit
            pre_commit_prompt = self.connection.find_prompt()
            logger.info(f"Pre-commit prompt: '{pre_commit_prompt}'")
            
            # Send commit command with enhanced expect patterns
            commit_output = self.connection.send_command(
                "commit", 
                expect_string=r'[\[\(].*[YyNnCc].*[\]\)]|#|>|\]$',
                delay_factor=4,
                max_loops=50
            )
            
            # Enhanced confirmation prompt detection
            confirmation_patterns = [
                'y/n/c', '[y/n/c]', '(y/n/c)', 
                'y/n', '[y/n]', '(y/n)',
                'confirm', 'continue', 'proceed'
            ]
            
            needs_confirmation = any(pattern in commit_output.lower() for pattern in confirmation_patterns)
            
            if needs_confirmation:
                logger.info("Detected commit confirmation prompt, responding with 'Y'")
                confirm_output = self.connection.send_command(
                    "Y", 
                    delay_factor=3,
                    max_loops=30
                )
                commit_output += "\n" + confirm_output
            
            # Verify commit completion
            post_commit_prompt = self.connection.find_prompt()
            logger.info(f"Post-commit prompt: '{post_commit_prompt}'")
            
            return commit_output
            
        except Exception as e:
            error_msg = f"Manual commit failed: {e}"
            logger.error(error_msg)
            return error_msg
    
    def _huawei_save_config(self) -> str:
        """Enhanced Huawei save configuration with better error handling"""
        try:
            logger.info("Saving Huawei configuration...")
            
            # Get current prompt before save
            pre_save_prompt = self.connection.find_prompt()
            logger.info(f"Pre-save prompt: '{pre_save_prompt}'")
            
            # Try Netmiko's save_config first
            try:
                if hasattr(self.connection, 'save_config'):
                    logger.info("Attempting save via Netmiko's save_config()")
                    save_output = self.connection.save_config()
                    
                    if save_output and "error" not in save_output.lower():
                        logger.info("Netmiko save_config() successful")
                        return save_output
                    else:
                        logger.info(f"Netmiko save_config() returned: {save_output[:100]}")
                        # Fall through to manual save
                        
            except Exception as netmiko_save_error:
                logger.info(f"Netmiko save_config() failed: {netmiko_save_error}")
                # Fall through to manual save
            
            # Manual save handling
            logger.info("Performing manual save operation")
            save_output = self.connection.send_command(
                "save",
                expect_string=r'[\[\(].*[YyNnCc].*[\]\)]|#|>|\]$',
                delay_factor=4,
                max_loops=50
            )
            
            # Enhanced confirmation detection for save
            confirmation_patterns = [
                'y/n/c', '[y/n/c]', '(y/n/c)',
                'y/n', '[y/n]', '(y/n)',
                'overwrite', 'confirm', 'continue'
            ]
            
            needs_confirmation = any(pattern in save_output.lower() for pattern in confirmation_patterns)
            
            if needs_confirmation:
                logger.info("Detected save confirmation prompt, responding with 'Y'")
                confirm_output = self.connection.send_command(
                    "Y",
                    delay_factor=3,
                    max_loops=30
                )
                save_output += "\n" + confirm_output
            
            # Verify save completion
            post_save_prompt = self.connection.find_prompt()
            logger.info(f"Post-save prompt: '{post_save_prompt}'")
            
            return save_output
            
        except Exception as e:
            error_msg = f"Save operation failed: {e}"
            logger.error(error_msg)
            return error_msg
    
    def _huawei_commit_and_save(self) -> str:
        """Legacy method - kept for backward compatibility"""
        return self._huawei_commit_and_save_enhanced()


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
        """Configure IPv4 address on interface."""
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
    
    def configure_ipv6_address(self, interface: str, ipv6_address: str, prefix_length: int) -> str:
        """Configure IPv6 address on interface."""
        if 'cisco' in self.device_type:
            commands = [
                f"interface {interface}",
                f"ipv6 address {ipv6_address}/{prefix_length}",
                "no shutdown"
            ]
        elif 'huawei' in self.device_type:
            commands = [
                f"interface {interface}",
                "ipv6 enable",
                f"ipv6 address {ipv6_address} {prefix_length}",
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
    
    def configure_vlan_interface_ipv6(self, vlan_id: int, ipv6_address: str, prefix_length: int, 
                                    vrf_name: str = None, description: str = None, enable: bool = True) -> str:
        """Configure VLAN interface IPv6 on Cisco/Huawei."""
        if 'cisco' in self.device_type:
            commands = [f"interface vlan {vlan_id}"]
            if description:
                commands.append(f"description {description}")
            if vrf_name:
                commands.append(f"ip vrf forwarding {vrf_name}")
            commands.append(f"ipv6 address {ipv6_address}/{prefix_length}")
            commands.append("no shutdown" if enable else "shutdown")
            return self.device.execute_config_commands(commands)
        elif 'huawei' in self.device_type:
            commands = [f"interface Vlanif{vlan_id}"]
            if description:
                commands.append(f"description {description}")
            if vrf_name:
                commands.append(f"ipv6 binding vpn-instance {vrf_name}")
            commands.extend([
                "ipv6 enable",
                f"ipv6 address {ipv6_address} {prefix_length}"
            ])
            commands.append("undo shutdown" if enable else "shutdown")
            commands.append("quit")
            return self.device.execute_config_commands(commands)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
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
    
    def add_static_route_v6(self, prefix: str, next_hop: str, vrf_name: str = None) -> str:
        """Add IPv6 static route."""
        if 'cisco' in self.device_type:
            if vrf_name:
                commands = [f"ipv6 route vrf {vrf_name} {prefix} {next_hop}"]
            else:
                commands = [f"ipv6 route {prefix} {next_hop}"]
        elif 'huawei' in self.device_type:
            if vrf_name:
                commands = [f"ipv6 route-static vpn-instance {vrf_name} {prefix} {next_hop}"]
            else:
                commands = [f"ipv6 route-static {prefix} {next_hop}"]
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
    
    def remove_static_route_v6(self, prefix: str, next_hop: str, vrf_name: str = None) -> str:
        """Remove IPv6 static route."""
        if 'cisco' in self.device_type:
            if vrf_name:
                commands = [f"no ipv6 route vrf {vrf_name} {prefix} {next_hop}"]
            else:
                commands = [f"no ipv6 route {prefix} {next_hop}"]
        elif 'huawei' in self.device_type:
            if vrf_name:
                commands = [f"undo ipv6 route-static vpn-instance {vrf_name} {prefix} {next_hop}"]
            else:
                commands = [f"undo ipv6 route-static {prefix} {next_hop}"]
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
            # Enter OSPF view, then set router id and areas/networks
            if vrf_name:
                commands = [
                    f"ospf {process_id} vpn-instance {vrf_name}"
                ]
            else:
                commands = [
                    f"ospf {process_id}"
                ]
            commands.append(f"router id {router_id}")
            for net in networks:
                area_val = self._normalize_area_id(str(net['area']))
                commands.extend([
                    f"area {area_val}",
                    f"network {net['network']} {net['wildcard']}",  # Huawei expects wildcard mask, not prefix length
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
    
    def _normalize_area_id(self, area: str) -> str:
        """Normalize Huawei OSPF area to dotted decimal (e.g., '0' -> '0.0.0.0')."""
        area = area.strip()
        if area.isdigit():
            num = int(area)
            a = (num >> 24) & 0xFF
            b = (num >> 16) & 0xFF
            c = (num >> 8) & 0xFF
            d = num & 0xFF
            return f"{a}.{b}.{c}.{d}"
        return area
    
    def show_routes(self, vrf_name: str = None) -> str:
        """Show routing table, optionally for a specific VRF."""
        if 'cisco' in self.device_type:
            if vrf_name:
                return self.device.execute_command(f"show ip route vrf {vrf_name}")
            else:
                return self.device.execute_command("show ip route")
        elif 'huawei' in self.device_type:
            if vrf_name:
                return self.device.execute_command(f"display ip routing-table vpn-instance {vrf_name}")
            else:
                return self.device.execute_command("display ip routing-table")
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")


class AEManager:
    """Aggregated Ethernet (AE) management for Juniper."""
    
    def __init__(self, device_manager: NetworkDeviceManager):
        self.device = device_manager
        self.device_type = device_manager.device_params['device_type']
    
    def create_ae(self, ae_name, members=None, lacp=True):
        if 'juniper' not in self.device_type:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        with self.device as dev:
            if dev.driver:
                commands = [f'set interfaces {ae_name} aggregated-ether-options lacp active'] if lacp else [f'set interfaces {ae_name}']
                if members:
                    for m in members:
                        commands.append(f'set interfaces {m} ether-options gigabit-options redundant-parent {ae_name}')
                return dev.driver.execute_config_commands(commands)
        
    def configure_ae_unit(self, ae_name, unit, ip_address, prefix_length, description=None):
        if 'juniper' not in self.device_type:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        with self.device as dev:
            if dev.driver:
                commands = [f'set interfaces {ae_name} unit {unit} family inet address {ip_address}/{prefix_length}']
                if description:
                    commands.append(f'set interfaces {ae_name} unit {unit} description "{description}"')
                return dev.driver.execute_config_commands(commands)

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
    
    def create_vrf(self, vrf_name: str, rd: str = None, description: str = None, import_rt: str = None, export_rt: str = None) -> str:
        """Create VRF on the device."""
        if 'cisco' in self.device_type:
            return self._create_cisco_vrf(vrf_name, rd, description, import_rt, export_rt)
        elif 'huawei' in self.device_type:
            return self._create_huawei_vrf(vrf_name, rd, description, import_rt, export_rt)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def _create_cisco_vrf(self, vrf_name: str, rd: str = None, description: str = None, import_rt: str = None, export_rt: str = None) -> str:
        """Create VRF on Cisco device."""
        commands = [f"ip vrf {vrf_name}"]
        if rd:
            commands.append(f"rd {rd}")
        if description:
            commands.append(f"description {description}")
        if import_rt:
            commands.append(f"route-target import {import_rt}")
        if export_rt:
            commands.append(f"route-target export {export_rt}")
        
        return self.device.execute_config_commands(commands)
    
    def _create_huawei_vrf(self, vrf_name: str, rd: str = None, description: str = None, import_rt: str = None, export_rt: str = None) -> str:
        """Create VRF on Huawei device."""
        commands = [f"ip vpn-instance {vrf_name}"]
        if rd:
            commands.append(f"route-distinguisher {rd}")
        if description:
            commands.append(f"description {description}")
        if import_rt:
            commands.append(f"vpn-target {import_rt} import-extcommunity")
        if export_rt:
            commands.append(f"vpn-target {export_rt} export-extcommunity")
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
    
    def configure_bgp_neighbor_v6(self, as_number: int, neighbor_ip: str, remote_as: int, vrf_name: str = None, description: str = None, source_interface: str = None) -> str:
        """Configure BGP IPv6 neighbor."""
        if 'cisco' in self.device_type:
            commands = [f"router bgp {as_number}"]
            if not vrf_name:
                commands.append(f"neighbor {neighbor_ip} remote-as {remote_as}")
                if description:
                    commands.append(f"neighbor {neighbor_ip} description {description}")
            commands.append(f"address-family ipv6{' vrf ' + vrf_name if vrf_name else ''}")
            commands.append(f"neighbor {neighbor_ip} remote-as {remote_as}")
            if description:
                commands.append(f"neighbor {neighbor_ip} description {description}")
            commands.append(f"neighbor {neighbor_ip} activate")
            commands.append("exit-address-family")
            return self.device.execute_config_commands(commands)
        elif 'huawei' in self.device_type:
            commands = [f"bgp {as_number}"]
            if vrf_name:
                commands.append(f"ipv6-family vpn-instance {vrf_name}")
            else:
                commands.append("ipv6-family")
            commands.append(f"peer {neighbor_ip} as-number {remote_as}")
            if description:
                commands.append(f"peer {neighbor_ip} description {description}")
            commands.extend(["quit", "quit"])
            return self.device.execute_config_commands(commands)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
    def advertise_network_v6(self, as_number: int, prefix: str, vrf_name: str = None) -> str:
        """Advertise IPv6 network in BGP."""
        if 'cisco' in self.device_type:
            commands = [
                f"router bgp {as_number}",
                f"address-family ipv6{' vrf ' + vrf_name if vrf_name else ''}",
                f"network {prefix}",
                "exit-address-family"
            ]
            return self.device.execute_config_commands(commands)
        elif 'huawei' in self.device_type:
            commands = [f"bgp {as_number}"]
            if vrf_name:
                commands.append(f"ipv6-family vpn-instance {vrf_name}")
            else:
                commands.append("ipv6-family")
            # Huawei expects prefix and length split; allow CIDR and pass as-is when possible
            # Typical syntax: network 2001:db8:: 64
            if '/' in prefix:
                net, plen = prefix.split('/')
                commands.append(f"network {net} {int(plen)}")
            else:
                commands.append(f"network {prefix}")
            commands.extend(["quit", "quit"])
            return self.device.execute_config_commands(commands)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
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
            vrf_commands.append(f"vpn-target {import_rt} import-extcommunity")
        if export_rt:
            vrf_commands.append(f"vpn-target {export_rt} export-extcommunity")
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
    
    def configure_ospf_v6(self, process_id: int, router_id: str, interfaces: List[Dict]) -> str:
        """Configure OSPFv3 (IPv6). interfaces: [{"interface": "GE1/0/1", "area": "0"}]"""
        if 'cisco' in self.device_type:
            commands = [
                "ipv6 unicast-routing",
                f"ipv6 router ospf {process_id}",
                f"router-id {router_id}",
                "exit"
            ]
            for itf in interfaces:
                commands.extend([
                    f"interface {itf['interface']}",
                    f"ipv6 ospf {process_id} area {itf['area']}",
                    "no shutdown"
                ])
            return self.device.execute_config_commands(commands)
        elif 'huawei' in self.device_type:
            commands = [
                f"ospfv3 {process_id}",
                f"router-id {router_id}",
                "quit"
            ]
            for itf in interfaces:
                commands.extend([
                    f"interface {itf['interface']}",
                    "ipv6 enable",
                    f"ospfv3 {process_id} area {itf['area']}",
                    "undo shutdown",
                    "quit"
                ])
            return self.device.execute_config_commands(commands)
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
    
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
    
    def configure_ospf_redistribution(self, process_id: int, protocol: str, metric: int = None, 
                                    metric_type: int = None, vrf_name: str = None) -> str:
        """Configure OSPF redistribution."""
        if 'cisco' in self.device_type:
            if vrf_name:
                commands = [f"router ospf {process_id} vrf {vrf_name}"]
            else:
                commands = [f"router ospf {process_id}"]
            
            cmd = f"redistribute {protocol}"
            if metric:
                cmd += f" metric {metric}"
            if metric_type:
                cmd += f" metric-type {metric_type}"
            commands.append(cmd)
            
        elif 'huawei' in self.device_type:
            if vrf_name:
                commands = [f"ospf {process_id} vpn-instance {vrf_name}"]
            else:
                commands = [f"ospf {process_id}"]
            
            cmd = f"import-route {protocol}"
            if metric:
                cmd += f" cost {metric}"
            if metric_type:
                cmd += f" type {metric_type}"
            commands.extend([cmd, "quit"])
        else:
            raise NetworkAutomationError(f"Unsupported device type: {self.device_type}")
        
        return self.device.execute_config_commands(commands)
    
    def _mask_to_prefix(self, mask: str) -> int:
        """Convert subnet mask to prefix length."""
        mask_parts = mask.split('.')
        binary = ''.join([bin(int(part))[2:].zfill(8) for part in mask_parts])
        return binary.count('1')


# Create alias for backward compatibility
OSPFManager = AdvancedOSPFManager


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
    
    def _ensure_evpn_overlay(self) -> str:
        """Ensure EVPN overlay feature is enabled and EVPN view initialized."""
        commands = [
            "evpn-overlay enable",
            "commit",
            "evpn",
            "commit",
            "quit"
        ]
        return self.device.execute_config_commands(commands)
    
    def _validate_huawei_connection(self, strict: bool = False) -> bool:
        """Test basic connectivity and Huawei command syntax before large operations."""
        validation_results = []
        
        try:
            logger.info("Validating Huawei device connectivity and command syntax...")
            
            # Test 1: Basic connectivity with simple commands
            test_commands = [
                ("display clock", "Clock display test"),
                ("display version", "Version information test")
            ]
            
            for cmd, description in test_commands:
                try:
                    result = self.device.execute_command(cmd)
                    if result and len(result.strip()) > 5:
                        logger.info(f"✓ {description}: PASSED ({len(result)} chars)")
                        validation_results.append(True)
                    else:
                        logger.warning(f"✗ {description}: FAILED - Minimal output: '{result[:50]}'")
                        validation_results.append(False)
                except Exception as e:
                    logger.warning(f"✗ {description}: FAILED - {e}")
                    validation_results.append(False)
            
            # Test 2: Configuration mode access
            try:
                logger.info("Testing system-view access...")
                result = self.device.execute_command("system-view")
                if "Error" in result or "Unrecognized" in result:
                    logger.warning(f"✗ System-view test: FAILED - {result[:100]}")
                    validation_results.append(False)
                else:
                    logger.info(f"✓ System-view test: PASSED")
                    validation_results.append(True)
                
                # Try to exit cleanly
                try:
                    self.device.execute_command("quit")
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"✗ System-view test: FAILED - {e}")
                validation_results.append(False)
            
            # Test 3: Interface command syntax
            try:
                logger.info("Testing interface command syntax...")
                # Test with a common interface that should exist
                result = self.device.execute_command("display interface brief")
                if result and len(result) > 20:
                    logger.info(f"✓ Interface command test: PASSED")
                    validation_results.append(True)
                else:
                    logger.warning(f"✗ Interface command test: FAILED - {result[:50]}")
                    validation_results.append(False)
            except Exception as e:
                logger.warning(f"✗ Interface command test: FAILED - {e}")
                validation_results.append(False)
            
            # Summarize results
            passed = sum(validation_results)
            total = len(validation_results)
            success_rate = (passed / total) * 100 if total > 0 else 0
            
            logger.info(f"Device validation summary: {passed}/{total} tests passed ({success_rate:.1f}%)")
            
            if strict:
                # All tests must pass for strict validation
                return all(validation_results)
            else:
                # At least 50% of tests must pass for lenient validation
                return success_rate >= 50
                
        except Exception as e:
            logger.error(f"Device validation failed with exception: {e}")
            return False
    
    def diagnose_device_connectivity(self) -> str:
        """Comprehensive device diagnostic to help troubleshoot connection issues."""
        diagnostics = []
        diagnostics.append("=== DEVICE CONNECTIVITY DIAGNOSTICS ===")
        
        # Test 1: Connection Health
        try:
            if self.device._check_connection_health():
                diagnostics.append("✓ Connection health: HEALTHY")
            else:
                diagnostics.append("✗ Connection health: UNHEALTHY")
        except Exception as e:
            diagnostics.append(f"✗ Connection health check failed: {e}")
        
        # Test 2: Basic Commands
        basic_commands = [
            "display version",
            "display clock", 
            "display current-configuration | include sysname",
            "display interface brief"
        ]
        
        for cmd in basic_commands:
            try:
                result = self.device.execute_command(cmd)
                if result and len(result.strip()) > 0:
                    diagnostics.append(f"✓ '{cmd}': SUCCESS ({len(result)} chars)")
                    # Show first line of output for context
                    first_line = result.strip().split('\n')[0][:60]
                    diagnostics.append(f"  Output preview: {first_line}")
                else:
                    diagnostics.append(f"✗ '{cmd}': FAILED - No output")
            except Exception as e:
                diagnostics.append(f"✗ '{cmd}': FAILED - {str(e)[:100]}")
        
        # Test 3: System View Access
        try:
            result = self.device.execute_command("system-view")
            if "Error" not in result and "Unrecognized" not in result:
                diagnostics.append("✓ System-view access: SUCCESS")
                # Try to exit
                try:
                    self.device.execute_command("quit")
                    diagnostics.append("✓ Exit from system-view: SUCCESS")
                except:
                    diagnostics.append("⚠ Exit from system-view: WARNING - May still be in config mode")
            else:
                diagnostics.append(f"✗ System-view access: FAILED - {result[:100]}")
        except Exception as e:
            diagnostics.append(f"✗ System-view access: FAILED - {e}")
        
        # Test 4: Device Type Detection
        device_type = self.device.device_params.get('device_type', 'unknown')
        diagnostics.append(f"Device type configured: {device_type}")
        
        # Test 5: Connection Parameters
        host = self.device.device_params.get('host', 'unknown')
        username = self.device.device_params.get('username', 'unknown')
        diagnostics.append(f"Connection target: {username}@{host}")
        
        diagnostics.append("=== END DIAGNOSTICS ===")
        
        return "\n".join(diagnostics)
    
    def _execute_commands_in_chunks(self, commands: List[str], chunk_size: int = 8) -> str:
        """Execute large command sets in smaller chunks with connection recovery."""
        results = []
        total_chunks = (len(commands) - 1) // chunk_size + 1
        failed_chunks = 0
        
        logger.info(f"Executing {len(commands)} commands in {total_chunks} chunks of {chunk_size}")
        
        for i in range(0, len(commands), chunk_size):
            chunk = commands[i:i + chunk_size]
            chunk_num = i // chunk_size + 1
            
            logger.info(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} commands)")
            
            # Try chunk execution with multiple attempts and connection recovery
            chunk_success = False
            max_chunk_retries = 3
            
            for attempt in range(max_chunk_retries):
                try:
                    # Check and restore connection before each chunk (especially after failures)
                    if attempt > 0 or failed_chunks > 0:
                        logger.info(f"Checking connection health before chunk {chunk_num}, attempt {attempt + 1}")
                        if not self.device._check_connection_health():
                            logger.warning(f"Connection unhealthy, attempting to reconnect for chunk {chunk_num}")
                            self.device._reconnect_if_needed()
                            # Give device time to stabilize after reconnection
                            time.sleep(2)
                    
                    result = self.device.execute_config_commands(chunk)
                    results.append(f"--- CHUNK {chunk_num} ---\n{result}")
                    chunk_success = True
                    logger.info(f"Chunk {chunk_num} completed successfully")
                    break
                    
                except Exception as e:
                    error_str = str(e).lower()
                    if ('socket is closed' in error_str or 'connection' in error_str or 
                        'broken pipe' in error_str) and attempt < max_chunk_retries - 1:
                        logger.warning(f"Chunk {chunk_num} attempt {attempt + 1} failed with connection error: {e}. Retrying...")
                        time.sleep(2)  # Longer pause before retry
                        continue
                    else:
                        logger.error(f"Chunk {chunk_num} failed after {attempt + 1} attempts: {e}")
                        results.append(f"--- CHUNK {chunk_num} FAILED ---\nError: {e}")
                        break
            
            if not chunk_success:
                failed_chunks += 1
                logger.warning(f"Chunk {chunk_num} could not be completed after {max_chunk_retries} attempts")
                # Try to reconnect for next chunk
                try:
                    logger.info("Attempting connection recovery for next chunk...")
                    self.device._reconnect_if_needed()
                except Exception as reconnect_error:
                    logger.error(f"Connection recovery failed: {reconnect_error}")
            
            # Pause between chunks to let the device process and recover
            if chunk_num < total_chunks:
                # Adaptive pause based on failure rate and chunk processing
                base_pause = 1
                failure_penalty = min(failed_chunks * 0.5, 3)  # Up to 3 extra seconds for failures
                pause_time = base_pause + failure_penalty
                
                logger.info(f"Pausing {pause_time:.1f}s before next chunk (base: {base_pause}s, failure penalty: {failure_penalty:.1f}s)...")
                time.sleep(pause_time)
                
                # Periodic connection health check every 5 chunks
                if chunk_num % 5 == 0:
                    logger.info(f"Periodic connection health check after chunk {chunk_num}")
                    if not self.device._check_connection_health():
                        logger.warning("Periodic health check failed, preemptively reconnecting")
                        try:
                            self.device._reconnect_if_needed()
                        except Exception as e:
                            logger.warning(f"Preemptive reconnection failed: {e}")
        
        success_rate = ((total_chunks - failed_chunks) / total_chunks) * 100
        summary = f"\n\n=== EXECUTION SUMMARY ===\nTotal chunks: {total_chunks}\nSuccessful: {total_chunks - failed_chunks}\nFailed: {failed_chunks}\nSuccess rate: {success_rate:.1f}%"
        
        return "\n\n".join(results) + summary
    
    def configure_spine_underlay(self, router_id: str, as_number: int, spine_interfaces: list,
                                spine_ip_range: str = "10.0.0.0/30",
                                underlay_links: list = None) -> str:
        """Configure spine switch underlay (BGP + OSPF) on Huawei."""
        commands = []
        
        # Configure OSPF for underlay (router id and area, then network statements)
        commands.extend([
            f"ospf 1 router-id {router_id}",  # Single-line to avoid context flip
            "ospf 1",
            "area 0.0.0.0"
        ])
        
        # Add /30 underlay networks and loopback to area 0
        if underlay_links:
            for link in sorted(underlay_links, key=lambda x: x['link_index']):
                net_ip = self._calculate_link_network(spine_ip_range, link['link_index'] - 1)
                commands.append(f"network {net_ip} 0.0.0.3")
        else:
            for idx, interface in enumerate(spine_interfaces):
                net_ip = self._calculate_link_network(spine_ip_range, idx)
                commands.append(f"network {net_ip} 0.0.0.3")
        # Advertise loopback as host
        commands.append(f"network {router_id} 0.0.0.0")
        # Exit area and OSPF view
        commands.extend(["quit", "quit"])
        
        # Ensure EVPN overlay is enabled before BGP EVPN
        try:
            self._ensure_evpn_overlay()
        except Exception:
            pass
        
        commands.extend([
            "interface LoopBack0",
            f"ip address {router_id} 255.255.255.255",
            "quit"
        ])
        # Configure base BGP on spine
        commands.extend([
            f"bgp {as_number}",
            f"router-id {router_id}",
        ])
        
           # Configure loopback address (no shutdown command on LoopBack)
        
        # If links provided, create external group and add peers to it
        if underlay_links:
            peer_as = link.get('peer_as') or as_number
            commands.extend([
                "group spine-leaf-evpn external"
            ])
            for link in sorted(underlay_links, key=lambda x: x['link_index']):
                peer_ip = link.get('peer_loopback_ip') or f"10.255.254.{link.get('peer_device_id', 1)}"
                peer_as = link.get('peer_as') or as_number
                commands.extend([
                    "undo default ipv4-unicast",
                    f"peer {peer_ip} as-number {peer_as}",
                    f"peer {peer_ip} connect-interface LoopBack0",
                    f"peer {peer_ip} ebgp-max-hop 2",
                    f"peer {peer_ip} group spine-leaf-evpn",
                    "l2vpn-family evpn",
                    f"peer {peer_ip} enable",
                    f"peer {peer_ip} advertise-community",
                    f"peer {peer_ip} reflect-client",
                    "quit",
                    f"bgp {as_number}"
                ])
            # EVPN settings for the group
          ##     "l2vpn-family evpn",
            #    "peer spine-leaf-evpn enable",
            #   "peer spine-leaf-evpn advertise-community",
             #   "peer spine-leaf-evpn reflect-client",
              #  "quit",
               # "quit"
            #])
        else:
            # No links provided: just exit BGP view cleanly
            commands.extend(["quit"])
        
      
        
        # Configure spine interfaces with IP addressing and enable
        if underlay_links:
            for link in sorted(underlay_links, key=lambda x: x['link_index']):
                base_ip = self._calculate_spine_ip(spine_ip_range, link['link_index'] - 1)
                iface = self._normalize_huawei_interface(link['local_interface'])
                commands.extend([
                    f"interface {iface}",
                    "undo portswitch",
                    f"ip address {base_ip} 255.255.255.252",
                    "undo shutdown",
                    "quit"
                ])
        else:
            for idx, interface in enumerate(spine_interfaces):
                base_ip = self._calculate_spine_ip(spine_ip_range, idx)
                iface = self._normalize_huawei_interface(interface)
                commands.extend([
                    f"interface {iface}",
                    "undo portswitch",
                    f"ip address {base_ip} 255.255.255.252",
                    "undo shutdown",
                    "quit"
                ])
        
       
        
        # Execute all commands in a single batch to preserve context
        return self.device.execute_config_commands(commands)
    
    def configure_leaf_underlay(self, router_id: str, as_number: int, spine_interfaces: list,
                               leaf_id: int, spine_ip_range: str = "10.0.0.0/30",
                               spine_peer_as_numbers: list = None,
                               uplink_spine_indices: list = None,
                               underlay_links: list = None) -> str:
        """Configure leaf switch underlay (BGP + OSPF) on Huawei.
        spine_peer_as_numbers: optional list of remote ASNs for each spine peer (order must
        match the implied spine loopback order 10.255.255.1, .2, ...). If not provided,
        falls back to using local as_number.
        uplink_spine_indices: optional list mapping each uplink interface to the target spine
        index (1-based) as ordered in the spine list; drives deterministic /30 selection.
        """
        commands = []
        
        # OSPF: set router id, area, and advertise networks
        commands.extend([
            f"ospf 1 router-id {router_id}",
            "ospf 1",
            "area 0.0.0.0"
        ])
        if underlay_links:
            for link in sorted(underlay_links, key=lambda x: x['link_index']):
                net_ip = self._calculate_link_network(spine_ip_range, link['link_index'] - 1)
                commands.append(f"network {net_ip} 0.0.0.3")
        else:
            for idx, interface in enumerate(spine_interfaces):
                net_index = (uplink_spine_indices[idx] - 1) if (uplink_spine_indices and idx < len(uplink_spine_indices)) else idx
                net_ip = self._calculate_link_network(spine_ip_range, net_index)
                commands.append(f"network {net_ip} 0.0.0.3")
        commands.append(f"network {router_id} 0.0.0.0")
        commands.extend(["quit", "quit"])
        
        # Ensure EVPN overlay is enabled before BGP EVPN
        try:
            self._ensure_evpn_overlay()
        except Exception:
            pass
        
        # BGP base with external group definition (stay in BGP view)
        commands.extend([
            f"bgp {as_number}",
            f"router-id {router_id}",
            "group spine-leaf-evpn external"
        ])
        
        # Configure loopback interface
        commands.extend([
            "interface LoopBack0",
            f"ip address {router_id} 255.255.255.255",
            "undo shutdown",
            "quit"
        ])
        
        # Configure leaf uplink interfaces to spines (L3 addressing)
        if underlay_links:
            for link in sorted(underlay_links, key=lambda x: x['link_index']):
                net_index = link['link_index'] - 1
                peer_ip = self._calculate_leaf_ip(spine_ip_range, leaf_id, net_index)
                iface = self._normalize_huawei_interface(link['local_interface'])
                commands.extend([
                    f"interface {iface}",
                    "undo portswitch",
                    f"ip address {peer_ip} 255.255.255.252",
                    "undo shutdown",
                    "quit"
                ])
        else:
            for idx, interface in enumerate(spine_interfaces):
                net_index = (uplink_spine_indices[idx] - 1) if (uplink_spine_indices and idx < len(uplink_spine_indices)) else idx
                peer_ip = self._calculate_leaf_ip(spine_ip_range, leaf_id, net_index)
                iface = self._normalize_huawei_interface(interface)
                commands.extend([
                    f"interface {iface}",
                    "undo portswitch",
                    f"ip address {peer_ip} 255.255.255.252",
                    "undo shutdown",
                    "quit"
                ])
        
        # Add spine peers to BGP for EVPN (assign to external group)
        if underlay_links:
            peers = [l.get('peer_loopback_ip') for l in sorted(underlay_links, key=lambda x: x['link_index'])]
            peer_ases = [l.get('peer_as', as_number) for l in sorted(underlay_links, key=lambda x: x['link_index'])]
            commands.extend([f"bgp {as_number}"])
            for spine_ip, remote_as in zip(peers, peer_ases):
                commands.extend([
                    "undo default ipv4-unicast",
                    f"peer {spine_ip} as-number {remote_as}",
                    f"peer {spine_ip} connect-interface LoopBack0",
                    f"peer {spine_ip} ebgp-max-hop 2",
                    "l2vpn-family evpn",
                    f"peer {spine_ip} enable",
                    f"peer {spine_ip} advertise-community",
                    "quit",
                ])
            # EVPN group enable
          #  commands.extend([
           #     "l2vpn-family evpn",
            #    "peer spine-leaf-evpn enable",
             #   "peer spine-leaf-evpn advertise-community",
              #  "quit",
            #])
        else:
            spine_loopbacks = self._get_spine_loopbacks(spine_interfaces)
            commands.extend([f"bgp {as_number}"])
            for idx, spine_ip in enumerate(spine_loopbacks):
                remote_as = (spine_peer_as_numbers[idx]
                             if spine_peer_as_numbers and idx < len(spine_peer_as_numbers)
                             else as_number)
                commands.extend([
                    f"peer {spine_ip} as-number {remote_as}",
                    f"peer {spine_ip} connect-interface LoopBack0",
                    f"peer {spine_ip} ebgp-max-hop 2",
                    f"l2vpn-family evpn",
                    f"peer {spine_ip} enable",
                    f"peer {spine_ip} advertise-community",
                ])
        
        # Execute in one go to preserve contexts
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
          #  f"evpn vpn-instance {tenant_name} bd-mode",
           # f"route-distinguisher auto",
          #  f"vpn-target {route_target} export-extcommunity",
           # f"vpn-target {route_target} import-extcommunity",
          #  "quit",
            
            # Create bridge domain
            f"bridge-domain {vlan_id}",
            f"vxlan vni {vni}",
            "arp broadcast-suppress enable",
            "evpn",
            f"route-distinguisher auto",
            f"vpn-target {route_target} export-extcommunity",
            f"vpn-target {route_target} import-extcommunity",
            "quit",
            
            # Create VLAN
            #f"vlan {vlan_id}",
            #f"description {tenant_name}_VLAN",
           # "quit",
            
            # Configure NVE interface (assuming NVE1 exists)
            "interface Nve1",
            f"vni {vni} head-end peer-list protocol bgp",
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
                    "port link-type trunk",
                    "quit",
                    f"interface {interface}.{vlan_id} mode l2",
                    f"encapsulation dot1q {vlan_id}",
                    f"bridge-domain {vlan_id}",
                    "undo shutdown",
                    "quit"
                ])
        
        return self.device.execute_config_commands(commands)
    
    def deploy_multi_tenant_configuration(self, fabric_name: str, tenant_networks: list) -> str:
        """Deploy multiple tenant networks with EVPN VXLAN configuration."""
        commands = []
        results = []
        
        # Add fabric description
        commands.extend([
            f"# Multi-Tenant Deployment for Fabric: {fabric_name}",
            f"# Deploying {len(tenant_networks)} tenant networks"
        ])
        
        # Process each tenant network
        for tenant in tenant_networks:
            tenant_name = tenant.get('name')
            vni = tenant.get('vni')
            vlan_id = tenant.get('vlan_id')
            gateway_ip = tenant.get('gateway_ip')
            subnet_mask = tenant.get('subnet_mask')
            access_interfaces = tenant.get('access_interfaces', [])
            route_target = tenant.get('route_target', f"65000:{vni}")
            advertise_external = tenant.get('advertise_external', False)
            
            if not all([tenant_name, vni, vlan_id, gateway_ip, subnet_mask]):
                error_msg = f"Missing required parameters for tenant {tenant_name}"
                results.append(f"ERROR: {error_msg}")
                continue
            
            # Generate commands for this tenant
            tenant_commands = self._generate_tenant_commands(
                tenant_name, vni, vlan_id, gateway_ip, 
                subnet_mask, access_interfaces, route_target
            )
            
            commands.extend(tenant_commands)
            results.append(f"✓ Configured tenant: {tenant_name} (VNI: {vni}, VLAN: {vlan_id})")
            
            # Configure external advertisement if requested
            if advertise_external:
                ext_commands = self._generate_external_advertisement_commands(
                    tenant_name, vni, route_target
                )
                commands.extend(ext_commands)
                results.append(f"✓ Configured external advertisement for: {tenant_name}")
        
        # Execute all commands in one batch for efficiency
        try:
            output = self.device.execute_config_commands(commands)
            results.append(f"\n=== Configuration Summary ===")
            results.append(f"Fabric: {fabric_name}")
            results.append(f"Total Tenants: {len(tenant_networks)}")
            results.append(f"Commands Executed: {len(commands)}")
            return "\n".join(results) + f"\n\n=== Device Output ===\n{output}"
            
        except Exception as e:
            error_msg = f"Failed to deploy multi-tenant configuration: {str(e)}"
            results.append(f"ERROR: {error_msg}")
            return "\n".join(results)
    
    def _generate_tenant_commands(self, tenant_name: str, vni: int, vlan_id: int,
                                 gateway_ip: str, subnet_mask: str, 
                                 access_interfaces: list = None, 
                                 route_target: str = None) -> list:
        """Generate configuration commands for a single tenant network."""
        prefix_length = self._mask_to_prefix(subnet_mask)
        
        commands = [
            f"# Tenant: {tenant_name} Configuration",
            
            # Create bridge domain
            f"bridge-domain {vlan_id}",
            f"vxlan vni {vni}",
            "arp broadcast-suppress enable",
            "evpn",
            f"route-distinguisher auto",
            f"vpn-target {route_target} export-extcommunity",
            f"vpn-target {route_target} import-extcommunity",
            "quit",
            
            # Create VLAN
           # f"vlan {vlan_id}",
           # f"description {tenant_name}_VLAN",
           # "quit",
            
            # Configure NVE interface
            "interface Nve1",
            f"vni {vni} head-end peer-list protocol bgp",
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
                    "port link-type trunk",
                    "quit",
                    f"interface {interface}.{vlan_id} mode l2",
                    f"encapsulation dot1q {vlan_id}",
                    f"bridge-domain {vlan_id}",
                    "undo shutdown",
                    "quit"
                ])
        
        return commands
    
    def _generate_external_advertisement_commands(self, tenant_name: str, vni: int, route_target: str) -> list:
        """Generate commands for external advertisement of tenant networks."""
        commands = [
            f"# External Advertisement for {tenant_name}",
            "bgp 65000",
            "l2vpn-family evpn",
            f"vpn-target {route_target} export-extcommunity",
            f"vpn-target {route_target} import-extcommunity",
            "quit",
            "quit"
        ]
        return commands
    
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
        # Check if validation should be skipped
        skip_validation = fabric_config.get('skip_validation', False)
        
        if not skip_validation:
            # First validate the device connection and basic functionality
            logger.info("Running device validation (set 'skip_validation': true to bypass)...")
            if not self._validate_huawei_connection(strict=False):
                logger.warning("Device validation failed with lenient checks")
                logger.info("Attempting with minimal validation...")
                
                # Try one more basic test
                try:
                    result = self.device.execute_command("display version")
                    if not result or len(result.strip()) < 10:
                        raise NetworkAutomationError(
                            "Device validation failed - cannot execute basic commands. "
                            "Check device connectivity and credentials. "
                            "You can bypass validation by adding 'skip_validation': true to fabric_config."
                        )
                    logger.info("Minimal validation passed, proceeding with configuration...")
                except Exception as e:
                    raise NetworkAutomationError(
                        f"Device validation failed: {e}. "
                        "You can bypass validation by adding 'skip_validation': true to fabric_config."
                    )
            else:
                logger.info("Device validation passed successfully")
        else:
            logger.warning("Device validation SKIPPED - proceeding without validation checks")
        
        device_role = fabric_config.get('device_role')  # 'spine' or 'leaf'
        device_id = fabric_config.get('device_id', 1)
        as_number = fabric_config.get('as_number', 65000)
        
        if device_role == 'spine':
            # Use loopback_ip from form, fallback to auto-generated
            router_id = fabric_config.get('loopback_ip') or f"10.255.255.{device_id}"
            spine_interfaces = fabric_config.get('spine_interfaces', [])
            spine_ip_range = fabric_config.get('underlay_ip_range', '10.0.0.0/30')
            return self.configure_spine_underlay(
                router_id, as_number, spine_interfaces, spine_ip_range,
                fabric_config.get('underlay_links')
            )
        
        elif device_role == 'leaf' or device_role == 'border_leaf':
            # Use loopback_ip from form, fallback to auto-generated
            router_id = fabric_config.get('loopback_ip') or f"10.255.254.{device_id}"
            # Use spine_interfaces from form (these are uplink interfaces on leaf)
            spine_interfaces = fabric_config.get('spine_interfaces', [])
            spine_ip_range = fabric_config.get('underlay_ip_range', '10.0.0.0/30')
            
            # Configure underlay
            result = self.configure_leaf_underlay(
                router_id, as_number, spine_interfaces, device_id, spine_ip_range,
                fabric_config.get('spine_peer_as_numbers'),
                fabric_config.get('uplink_spine_indices'),
                fabric_config.get('underlay_links')
            )
            
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
            if device_role == 'border_leaf':
                # For border leaf, configure basic external connectivity
                external_config = {
                    'vrf_name': 'EXTERNAL_VRF',
                    'as_number': as_number,
                    'rd': 'auto',
                    'rt': '65000:999'
                }
                external_result = self.configure_external_connectivity(external_config)
                result += "\n\n--- EXTERNAL CONNECTIVITY ---\n" + external_result
            
            return result
        
        else:
            raise NetworkAutomationError(f"Unknown device role: {device_role}")
    
    def deploy_single_switch_to_fabric(self, fabric_config: dict) -> str:
        """Deploy a single switch to an existing fabric with proper peer configuration."""
        from .models import FabricDeployment, Device
        
        # Check if validation should be skipped
        skip_validation = fabric_config.get('skip_validation', False)
        
        if not skip_validation:
            # First validate device connection and basic functionality
            logger.info("Running device validation (set 'skip_validation': true to bypass)...")
            if not self._validate_huawei_connection(strict=False):
                logger.warning("Device validation failed with lenient checks")
                logger.info("Attempting with minimal validation...")
                
                # Try one more basic test
                try:
                    result = self.device.execute_command("display version")
                    if not result or len(result.strip()) < 10:
                        raise NetworkAutomationError(
                            "Device validation failed - cannot execute basic commands. "
                            "Check device connectivity and credentials. "
                            "You can bypass validation by adding 'skip_validation': true to fabric_config."
                        )
                    logger.info("Minimal validation passed, proceeding with configuration...")
                except Exception as e:
                    raise NetworkAutomationError(
                        f"Device validation failed: {e}. "
                        "You can bypass validation by adding 'skip_validation': true to fabric_config."
                    )
            else:
                logger.info("Device validation passed successfully")
        else:
            logger.warning("Device validation SKIPPED - proceeding without validation checks")
        
        device_role = fabric_config.get('device_role')  # 'spine' or 'leaf'
        device_id = fabric_config.get('device_id', 1)
        as_number = fabric_config.get('as_number', 65000)
        fabric_name = fabric_config.get('fabric_name')
        
        if not fabric_name:
            raise NetworkAutomationError("fabric_name is required for single switch deployment")
        
        # Get fabric deployment record
        try:
            fabric_deployment = FabricDeployment.objects.get(fabric_name=fabric_name)
            logger.info(f"Found existing fabric: {fabric_name}")
        except FabricDeployment.DoesNotExist:
            raise NetworkAutomationError(f"Fabric '{fabric_name}' not found. Create fabric first.")
        
        # Get current device ID from database
        current_device_id = fabric_config.get('current_device_id')
        if not current_device_id:
            raise NetworkAutomationError("current_device_id is required for fabric tracking")
        
        # Generate configuration based on device role
        if device_role == 'spine':
            # Use loopback_ip from form, fallback to auto-generated
            router_id = fabric_config.get('loopback_ip') or f"10.255.255.{device_id}"
            spine_interfaces = fabric_config.get('spine_interfaces', [])
            spine_ip_range = fabric_deployment.underlay_ip_range
            
            # Get leaf devices from fabric for BGP peering
            leaf_devices = fabric_deployment.leaf_devices
            spine_peer_as_numbers = []
            
            # Configure spine underlay with peer information
            result = self.configure_spine_underlay(
                router_id, as_number, spine_interfaces, spine_ip_range,
                fabric_config.get('underlay_links', [])
            )
            
            # Update fabric deployment with this spine
            spine_config = {
                'device_id': current_device_id,
                'name': fabric_config.get('device_name', f'spine-{device_id}'),
                'router_id': router_id,
                'as_number': as_number,
                'interfaces': spine_interfaces,
                'loopback_ip': router_id
            }
            
            # Add or update spine in fabric
            fabric_deployment.spine_devices = [
                s for s in fabric_deployment.spine_devices 
                if s['device_id'] != current_device_id
            ] + [spine_config]
            
        elif device_role == 'leaf' or device_role == 'border_leaf':
            # Use loopback_ip from form, fallback to auto-generated
            router_id = fabric_config.get('loopback_ip') or f"10.255.254.{device_id}"
            # Use spine_interfaces from form (these are uplink interfaces on leaf)
            spine_interfaces = fabric_config.get('spine_interfaces', [])
            spine_ip_range = fabric_deployment.underlay_ip_range
            
            # Get spine devices from fabric for BGP peering
            spine_devices = fabric_deployment.spine_devices
            spine_peer_as_numbers = [s['as_number'] for s in spine_devices]
            uplink_spine_indices = []
            
            # Determine spine indices for uplinks
            for i, interface in enumerate(spine_interfaces):
                # Find corresponding spine by interface name pattern or order
                if i < len(spine_devices):
                    uplink_spine_indices.append(i + 1)  # Spine indices are 1-based
            
            # Configure leaf underlay with spine peer information
            result = self.configure_leaf_underlay(
                router_id, as_number, spine_interfaces, device_id, spine_ip_range,
                spine_peer_as_numbers,
                uplink_spine_indices,
                fabric_config.get('underlay_links', [])
            )
            
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
            
            # Deploy tenant networks from fabric
            tenant_networks = fabric_deployment.tenant_networks
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
            if device_role == 'border_leaf':
                # For border leaf, configure basic external connectivity
                external_config = {
                    'vrf_name': 'EXTERNAL_VRF',
                    'as_number': as_number,
                    'rd': 'auto',
                    'rt': '65000:999'
                }
                external_result = self.configure_external_connectivity(external_config)
                result += "\n\n--- EXTERNAL CONNECTIVITY ---\n" + external_result
            
            # Update fabric deployment with this leaf
            leaf_config = {
                'device_id': current_device_id,
                'name': fabric_config.get('device_name', f'leaf-{device_id}'),
                'router_id': router_id,
                'as_number': as_number,
                'interfaces': spine_interfaces,
                'loopback_ip': router_id,
                'is_border_leaf': device_role == 'border_leaf'
            }
            
            # Add or update leaf in appropriate list
            if device_role == 'border_leaf':
                fabric_deployment.border_leaf_devices = [
                    bl for bl in fabric_deployment.border_leaf_devices 
                    if bl['device_id'] != current_device_id
                ] + [leaf_config]
            else:
                fabric_deployment.leaf_devices = [
                    l for l in fabric_deployment.leaf_devices 
                    if l['device_id'] != current_device_id
                ] + [leaf_config]
        
        else:
            raise NetworkAutomationError(f"Unknown device role: {device_role}")
        
        # Save fabric deployment updates
        fabric_deployment.save()
        
        # Add configuration summary
        summary = f"\n\n=== FABRIC DEPLOYMENT SUMMARY ===\n"
        summary += f"Fabric: {fabric_name}\n"
        summary += f"Device Role: {device_role}\n"
        summary += f"Device ID: {device_id}\n"
        summary += f"Router ID: {router_id}\n"
        summary += f"AS Number: {as_number}\n"
        summary += f"Total Spines in Fabric: {len(fabric_deployment.spine_devices)}\n"
        summary += f"Total Leaves in Fabric: {len(fabric_deployment.leaf_devices)}\n"
        summary += f"Total Border Leaves in Fabric: {len(fabric_deployment.border_leaf_devices)}\n"
        summary += f"Total Tenant Networks: {len(fabric_deployment.tenant_networks)}\n"
        
        return result + summary
    
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
        octets[3] = str(int(octets[3]) + (interface_idx * 4) + 2)  # second usable in /30 for leaf
        return '.'.join(octets)
    
    def _get_spine_loopbacks(self, spine_interfaces: list) -> list:
        """Get spine loopback addresses for BGP peering."""
        # Return predefined spine loopbacks - in production, this would be dynamic
        return [f"10.255.255.{i+1}" for i in range(len(spine_interfaces))]
    
    def _calculate_link_network(self, ip_range: str, interface_idx: int) -> str:
        """Calculate /30 network address for given link index based on base ip_range."""
        base_ip = ip_range.split('/')[0]
        octets = base_ip.split('.')
        octets[3] = str(int(octets[3]) + (interface_idx * 4))
        return '.'.join(octets)
    
    def _normalize_huawei_interface(self, name: str) -> str:
        """Normalize Huawei interface names conservatively (keep GE as-is)."""
        n = name.strip()
        if n.startswith('GE'):
            return n  # Keep short GE naming which your device accepts
        if n.startswith('XGE'):
            return '10GE' + n[3:]
        if n.lower().startswith('loopback'):
            # Huawei uses LoopBack with capital B sometimes; accept both
            return 'LoopBack' + n.split('loopback',1)[-1] if 'loopback' in n.lower() else n
        return n
    
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
            
            elif task_type == 'interface_ipv6':
                manager = InterfaceManager(device)
                result = manager.configure_ipv6_address(
                    parameters['interface'],
                    parameters['ipv6_address'],
                    parameters['prefix_length']
                )
            
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
            
            elif task_type == 'vlan_interface_ipv6':
                manager = InterfaceManager(device)
                result = manager.configure_vlan_interface_ipv6(
                    parameters['vlan_id'],
                    parameters['ipv6_address'],
                    parameters['prefix_length'],
                    parameters.get('vrf_name'),
                    parameters.get('description'),
                    parameters.get('enable_interface', True)
                )
            
            elif task_type == 'routing_ospf':
                manager = RoutingManager(device)
                result = manager.configure_ospf(
                    parameters['process_id'],
                    parameters['router_id'],
                    parameters['networks'],
                    parameters.get('vrf_name')
                    )
            
            elif task_type == 'routing_static_v6':
                manager = RoutingManager(device)
                if parameters.get('action') == 'remove':
                    result = manager.remove_static_route_v6(
                        parameters['prefix'],
                        parameters['next_hop'],
                        parameters.get('vrf_name')
                    )
                else:
                    result = manager.add_static_route_v6(
                        parameters['prefix'],
                        parameters['next_hop'],
                        parameters.get('vrf_name')
                )
            
            elif task_type == 'bgp_neighbor_v6':
                manager = BGPManager(device)
                result = manager.configure_bgp_neighbor_v6(
                    parameters['as_number'],
                    parameters['neighbor_ip'],
                    parameters['remote_as'],
                    parameters.get('vrf_name'),
                    parameters.get('description'),
                    parameters.get('source_interface')
                )
            
            elif task_type == 'bgp_network_v6':
                manager = BGPManager(device)
                result = manager.advertise_network_v6(
                    parameters['as_number'],
                    parameters['prefix'],
                    parameters.get('vrf_name')
                )
            
            elif task_type == 'routing_ospf_v6':
                manager = OSPFManager(device)
                result = manager.configure_ospf_v6(
                    parameters['process_id'],
                    parameters['router_id'],
                    parameters['interfaces']
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
                result = manager.show_routes(parameters.get('vrf_name'))
            
            elif task_type == 'show_vrfs':
                manager = VRFManager(device)
                result = manager.show_vrfs()
            
            elif task_type == 'backup_config':
                manager = DeviceInfoManager(device)
                result = manager.backup_config()
            
            # VRF tasks
            elif task_type == 'vrf_create':
                manager = VRFManager(device)
                result = manager.create_vrf(
                    parameters['vrf_name'],
                    parameters.get('rd'),
                    parameters.get('description'),
                    parameters.get('import_rt'),
                    parameters.get('export_rt')
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
            
            # Advanced BGP tasks
            elif task_type == 'bgp_route_reflector':
                manager = BGPManager(device)
                result = manager.configure_bgp_route_reflector(
                    parameters['as_number'],
                    parameters['router_id'],
                    parameters.get('cluster_id', 1),
                    parameters.get('clients', [])
                )
            
            elif task_type == 'bgp_confederation':
                manager = BGPManager(device)
                result = manager.configure_bgp_confederation(
                    parameters['as_number'],
                    parameters['confederation_id'],
                    parameters.get('confederation_peers', [])
                )
            
            elif task_type == 'bgp_community':
                manager = BGPManager(device)
                result = manager.configure_bgp_community(
                    parameters['as_number'],
                    parameters['community_list'],
                    parameters.get('action', 'permit')
                )
            
            elif task_type == 'bgp_route_map':
                manager = BGPManager(device)
                result = manager.configure_bgp_route_map(
                    parameters['as_number'],
                    parameters['route_map'],
                    parameters['neighbor_ip'],
                    parameters.get('direction', 'in')
                )
            
            elif task_type == 'bgp_multipath':
                manager = BGPManager(device)
                result = manager.configure_bgp_multipath(
                    parameters['as_number'],
                    parameters.get('ebgp_paths', 4),
                    parameters.get('ibgp_paths', 4)
                )
            
            # Advanced OSPF tasks
            elif task_type == 'ospf_area':
                manager = OSPFManager(device)
                result = manager.configure_ospf_area(
                    parameters['process_id'],
                    parameters['area_id'],
                    parameters.get('area_type', 'standard'),
                    parameters.get('stub_default_cost'),
                    parameters.get('nssa_default_route', False)
                )
            
            elif task_type == 'ospf_authentication':
                manager = OSPFManager(device)
                result = manager.configure_ospf_authentication(
                    parameters['process_id'],
                    parameters.get('area_id'),
                    parameters.get('interface'),
                    parameters.get('auth_type', 'md5'),
                    parameters.get('key_id', 1),
                    parameters.get('password', 'cisco123')
                )
            
            elif task_type == 'ospf_redistribution':
                manager = OSPFManager(device)
                result = manager.configure_ospf_redistribution(
                    parameters['process_id'],
                    parameters['protocol'],
                    parameters.get('metric'),
                    parameters.get('metric_type'),
                    parameters.get('vrf_name')
                )
            
            # EVPN tasks
            elif task_type == 'evpn_instance':
                manager = JuniperEVPNManager(device)
                result = manager.create_evpn_instance(
                    parameters['instance_name'],
                    parameters['vpls_id'],
                    parameters.get('rd'),
                    parameters.get('route_target'),
                    parameters.get('route_target_id'),
                    parameters.get('encapsulation', 'mpls'),
                    parameters.get('replication_type', 'ingress'),
                    parameters.get('description')
                )
            
            elif task_type == 'bgp_evpn':
                manager = EVPNManager(device)
                result = manager.configure_bgp_evpn(
                    parameters['as_number'],
                    parameters['neighbor_ip'],
                    parameters.get('source_interface')
                )
            
            elif task_type == 'vbdif_interface':
                manager = EVPNManager(device)
                result = manager.configure_vbdif_interface(
                    parameters['vbdif_id'],
                    parameters['ip_address'],
                    parameters['mask'],
                    parameters['bridge_domain']
                )
            
            elif task_type == 'bridge_domain':
                manager = JuniperEVPNManager(device)
                result = manager.add_bridge_domain_to_evpn(
                    parameters['instance_name'],
                    parameters['bd_name'],
                    parameters['vlan_id'],
                    parameters.get('interface'),
                    parameters.get('description')
                )
            
            elif task_type == 'evpn_ethernet_segment':
                manager = EVPNManager(device)
                result = manager.configure_evpn_ethernet_segment(
                    parameters['interface'],
                    parameters['esi'],
                    parameters.get('df_election', 'mod')
                )
            
            # VXLAN tasks
            elif task_type == 'vxlan_tunnel':
                manager = VXLANManager(device)
                result = manager.configure_vxlan_tunnel(
                    parameters['tunnel_id'],
                    parameters['source_ip'],
                    parameters['destination_ip'],
                    parameters['vni']
                )
            
            elif task_type == 'nve_interface':
                manager = VXLANManager(device)
                vni_mapping = parameters.get('vni_mapping') or parameters.get('vni_mappings')
                if isinstance(vni_mapping, list):
                    try:
                        vni_mapping = {item['vni']: item['bridge_domain'] for item in vni_mapping}
                    except Exception:
                        vni_mapping = {}
                elif not isinstance(vni_mapping, dict):
                    vni_mapping = {}
                result = manager.configure_nve_interface(
                    parameters['nve_id'],
                    parameters['source_ip'],
                    vni_mapping
                )
            
            elif task_type == 'vxlan_bd_binding':
                manager = VXLANManager(device)
                result = manager.configure_vxlan_bd_binding(
                    parameters['bd_id'],
                    parameters['vni'],
                    parameters['nve_interface']
                )
            
            elif task_type == 'vxlan_access_port':
                manager = VXLANManager(device)
                bd_id = parameters.get('bd_id') or parameters.get('bridge_domain_id')
                result = manager.configure_vxlan_access_port(
                    parameters['interface'],
                    bd_id
                )
            
            elif task_type == 'vxlan_gateway':
                manager = VXLANManager(device)
                bd_id = parameters.get('bd_id') or parameters.get('bridge_domain_id')
                mask = parameters.get('mask') or parameters.get('subnet_mask')
                result = manager.configure_vxlan_gateway(
                    bd_id,
                    parameters['gateway_ip'],
                    mask,
                    parameters.get('vbdif_id')
                )
            
            # Datacenter Fabric tasks
            elif task_type == 'ae_config':
                manager = AEManager(device)
                result = manager.create_ae(
                    parameters['ae_name'],
                    parameters.get('members', []),
                    parameters.get('lacp', True)
                )
                if parameters.get('ip_address') and parameters.get('prefix_length'):
                    result += ' ' + manager.configure_ae_unit(
                        parameters['ae_name'],
                        parameters['unit'],
                        parameters['ip_address'],
                        parameters['prefix_length'],
                        parameters.get('description')
                    )
            
            # EVPN/L2VPN task handlers
            elif task_type == 'l2vpws':
                if JuniperEVPNManager:
                    manager = JuniperEVPNManager(device)
                    result = manager.create_l2vpws(
                        parameters['service_name'],
                        parameters['local_if'],
                        parameters['remote_ip'],
                        parameters['vc_id'],
                        parameters.get('description')
                    )
                else:
                    raise NetworkAutomationError("EVPNManager not available")
            
            elif task_type == 'l2vpn_vpls':
                if JuniperEVPNManager:
                    manager = JuniperEVPNManager(device)
                    result = manager.create_l2vpn_vpls(
                        parameters['service_name'],
                        parameters['vpls_id'],
                        parameters.get('rd'),
                        parameters.get('rt_both'),
                        parameters.get('description')
                    )
                else:
                    raise NetworkAutomationError("EVPNManager not available")
            elif task_type == 'datacenter_fabric':
                manager = DataCenterFabricManager(device)
                # Pass parameters directly as fabric_config
                fabric_config = parameters
                result = manager.deploy_full_fabric_configuration(fabric_config)
            
            elif task_type == 'datacenter_fabric_single':
                manager = DataCenterFabricManager(device)
                # Pass parameters directly as fabric_config
                fabric_config = parameters
                result = manager.deploy_single_switch_to_fabric(fabric_config)
            
            elif task_type == 'spine_underlay':
                manager = DataCenterFabricManager(device)
                result = manager.configure_spine_underlay(
                    parameters['router_id'],
                    parameters['as_number'],
                    parameters['spine_interfaces'],
                    parameters.get('spine_ip_range', '10.0.0.0/30')
                )
            
            elif task_type == 'leaf_underlay':
                manager = DataCenterFabricManager(device)
                result = manager.configure_leaf_underlay(
                    parameters['router_id'],
                    parameters['as_number'],
                    parameters['spine_interfaces'],
                    parameters['leaf_id']
                )
            
            elif task_type == 'tenant_network':
                manager = DataCenterFabricManager(device)
                result = manager.deploy_tenant_network(
                    parameters['tenant_name'],
                    parameters['vni'],
                    parameters['vlan_id'],
                    parameters['gateway_ip'],
                    parameters['subnet_mask'],
                    parameters.get('access_interfaces', []),
                    parameters.get('route_target')
                )
            
            elif task_type == 'external_connectivity':
                manager = DataCenterFabricManager(device)
                result = manager.configure_external_connectivity(
                    parameters['border_leaf_config']
                )
            
            elif task_type == 'device_diagnostics':
                manager = DataCenterFabricManager(device)
                result = manager.diagnose_device_connectivity()
            
            elif task_type == 'multi_tenant_deployment':
                manager = DataCenterFabricManager(device)
                result = manager.deploy_multi_tenant_configuration(
                    parameters['fabric_name'],
                    parameters['tenant_networks']
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
