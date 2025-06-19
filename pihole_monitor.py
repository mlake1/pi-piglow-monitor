#!/usr/bin/env python3
"""
Pi-hole PiGlow System Monitor
Displays Pi-hole status and system metrics using PiGlow LEDs

Requirements:
- sudo pip3 install piglow requests psutil
- Pi-hole running on same system
- PiGlow connected to GPIO
"""

import time
import json
import requests
import psutil
from piglow import PiGlow
import subprocess
import os
import sys

class PiHolePiGlowMonitor:
    def __init__(self, config_file="config.json"):
        self.piglow = PiGlow()
        self.config = self.load_config(config_file)
        self.pihole_api_url = self.config.get("pihole_api_url", "http://localhost/admin/api.php")
        
        # LED mapping for different metrics
        self.status_colors = {
            'enabled': self.config["colors"]["pihole_enabled"],
            'disabled': self.config["colors"]["pihole_disabled"],
            'error': self.config["colors"]["pihole_error"]
        }
        
        # Arms: 0=top-right, 1=bottom, 2=top-left
        self.metric_arms = {
            'pihole_status': self.config["led_mapping"]["pihole_status_arm"],
            'system_health': self.config["led_mapping"]["system_health_arm"],
            'network_activity': self.config["led_mapping"]["network_activity_arm"]
        }
        
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        default_config = {
            "pihole_api_url": "http://localhost/admin/api.php",
            "update_interval": 10,
            "temperature_warning": 60,
            "temperature_critical": 70,
            "cpu_warning": 80,
            "memory_warning": 85,
            "brightness_scale": 1.0,
            "enable_startup_animation": True,
            "led_mapping": {
                "pihole_status_arm": 0,
                "system_health_arm": 1,
                "network_activity_arm": 2
            },
            "colors": {
                "pihole_enabled": "green",
                "pihole_disabled": "red",
                "pihole_error": "orange",
                "cpu_usage": "blue",
                "memory_usage": "white",
                "temperature_warning": "orange",
                "temperature_critical": "red",
                "network_queries": "yellow",
                "blocked_queries": "red"
            },
            "thresholds": {
                "high_cpu": 75,
                "high_memory": 80,
                "high_disk": 90,
                "high_queries_per_minute": 100
            },
            "features": {
                "enable_system_monitoring": True,
                "enable_network_monitoring": True,
                "enable_temperature_monitoring": True,
                "enable_error_alerts": True,
                "enable_startup_sequence": True
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                # Merge user config with defaults
                config = default_config.copy()
                config.update(user_config)
                return config
            else:
                print(f"Config file {config_file} not found, using defaults")
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            return default_config
        
    def get_pihole_status(self):
        """Get Pi-hole status and statistics"""
        try:
            # Basic status
            response = requests.get(self.pihole_api_url, timeout=5)
            data = response.json()
            
            # Extended stats
            stats_response = requests.get(f"{self.pihole_api_url}?summaryRaw", timeout=5)
            stats_data = stats_response.json()
            
            return {
                'status': data.get('status', 'unknown'),
                'domains_blocked': int(data.get('domains_being_blocked', 0)),
                'queries_today': int(stats_data.get('dns_queries_today', 0)),
                'blocked_today': int(stats_data.get('ads_blocked_today', 0)),
                'percent_blocked': float(stats_data.get('ads_percentage_today', 0)),
                'clients': int(stats_data.get('unique_clients', 0))
            }
        except Exception as e:
            print(f"Error getting Pi-hole status: {e}")
            return None
    
    def get_system_metrics(self):
        """Get system health metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Temperature (Raspberry Pi specific)
            try:
                temp_output = subprocess.check_output(['vcgencmd', 'measure_temp'])
                temp_celsius = float(temp_output.decode().strip().split('=')[1].split("'")[0])
            except:
                temp_celsius = 0
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'temperature': temp_celsius,
                'disk_percent': disk_percent
            }
        except Exception as e:
            print(f"Error getting system metrics: {e}")
            return None
    
    def display_pihole_status(self, pihole_data):
        """Display Pi-hole status on designated arm"""
        arm = self.metric_arms['pihole_status']
        
        if not pihole_data:
            # Error state - flash orange
            self.piglow.arm(arm, 0)
            for _ in range(3):
                self.piglow.color(self.status_colors['error'], 100)
                time.sleep(0.3)
                self.piglow.color(self.status_colors['error'], 0)
                time.sleep(0.3)
            return
        
        # Clear arm first
        self.piglow.arm(arm, 0)
        
        if pihole_data['status'] == 'enabled':
            # Green intensity based on blocking percentage
            intensity = min(100, max(20, int(pihole_data['percent_blocked'] * 2)))
            intensity = int(intensity * self.config["brightness_scale"])
            self.piglow.color(self.status_colors['enabled'], intensity)
        else:
            # Red if disabled
            intensity = int(100 * self.config["brightness_scale"])
            self.piglow.color(self.status_colors['disabled'], intensity)
    
    def display_system_health(self, system_data):
        """Display system health on designated arm"""
        arm = self.metric_arms['system_health']
        
        if not system_data or not self.config["features"]["enable_system_monitoring"]:
            return
        
        # Clear arm first
        self.piglow.arm(arm, 0)
        
        # Temperature check first (highest priority)
        if (self.config["features"]["enable_temperature_monitoring"] and 
            system_data['temperature'] > self.config["temperature_critical"]):
            intensity = int(100 * self.config["brightness_scale"])
            self.piglow.color(self.config["colors"]["temperature_critical"], intensity)
            return
        elif (self.config["features"]["enable_temperature_monitoring"] and 
              system_data['temperature'] > self.config["temperature_warning"]):
            intensity = int(80 * self.config["brightness_scale"])
            self.piglow.color(self.config["colors"]["temperature_warning"], intensity)
            return
        
        # Normal operation - show CPU and memory
        # CPU usage (blue)
        cpu_intensity = min(100, max(10, int(system_data['cpu_percent'])))
        cpu_intensity = int(cpu_intensity * self.config["brightness_scale"])
        
        # Memory usage (white)
        memory_intensity = min(100, max(10, int(system_data['memory_percent'])))
        memory_intensity = int(memory_intensity * self.config["brightness_scale"])
        
        # Show both CPU and memory
        self.piglow.color(self.config["colors"]["cpu_usage"], cpu_intensity)
        time.sleep(0.1)
        self.piglow.color(self.config["colors"]["memory_usage"], memory_intensity)
    
    def display_network_activity(self, pihole_data):
        """Display network activity on designated arm"""
        arm = self.metric_arms['network_activity']
        
        if not pihole_data or not self.config["features"]["enable_network_monitoring"]:
            return
        
        # Clear arm first
        self.piglow.arm(arm, 0)
        
        # Query activity visualization
        queries = pihole_data['queries_today']
        blocked = pihole_data['blocked_today']
        
        # Scale to reasonable display range
        if queries > 0:
            # Yellow for total queries (scaled)
            query_intensity = min(100, max(10, int(queries / 100)))
            query_intensity = int(query_intensity * self.config["brightness_scale"])
            self.piglow.color(self.config["colors"]["network_queries"], query_intensity)
            
            time.sleep(0.1)
            
            # Red for blocked queries
            if blocked > 0:
                blocked_intensity = min(100, max(10, int(blocked / 50)))
                blocked_intensity = int(blocked_intensity * self.config["brightness_scale"])
                self.piglow.color(self.config["colors"]["blocked_queries"], blocked_intensity)
    
    def startup_sequence(self):
        """Fun startup animation"""
        if not self.config["features"]["enable_startup_sequence"]:
            return
            
        print("Pi-hole PiGlow Monitor Starting...")
        
        # Rainbow startup
        colors = ['red', 'orange', 'yellow', 'green', 'blue', 'white']
        for color in colors:
            intensity = int(100 * self.config["brightness_scale"])
            self.piglow.color(color, intensity)
            time.sleep(0.2)
            self.piglow.color(color, 0)
        
        # Arm sweep
        for arm in range(3):
            intensity = int(100 * self.config["brightness_scale"])
            self.piglow.arm(arm, intensity)
            time.sleep(0.2)
            self.piglow.arm(arm, 0)
        
        print("Monitor active!")
    
    def error_alert(self):
        """Flash error pattern"""
        if not self.config["features"]["enable_error_alerts"]:
            return
            
        for _ in range(5):
            intensity = int(100 * self.config["brightness_scale"])
            self.piglow.all(intensity)
            time.sleep(0.2)
            self.piglow.all(0)
            time.sleep(0.2)
    
    def run_monitor(self, update_interval=None):
        """Main monitoring loop"""
        if update_interval is None:
            update_interval = self.config["update_interval"]
            
        self.startup_sequence()
        
        try:
            while True:
                print(f"\n--- Update at {time.strftime('%H:%M:%S')} ---")
                
                # Get data
                pihole_data = self.get_pihole_status()
                system_data = self.get_system_metrics()
                
                # Display status
                if pihole_data:
                    print(f"Pi-hole: {pihole_data['status']} | "
                          f"Queries: {pihole_data['queries_today']} | "
                          f"Blocked: {pihole_data['blocked_today']} "
                          f"({pihole_data['percent_blocked']:.1f}%)")
                else:
                    print("Pi-hole: ERROR - Cannot connect to API")
                    self.error_alert()
                
                if system_data:
                    print(f"System: CPU {system_data['cpu_percent']:.1f}% | "
                          f"Memory {system_data['memory_percent']:.1f}% | "
                          f"Temp {system_data['temperature']:.1f}°C")
                
                # Update display
                self.display_pihole_status(pihole_data)
                time.sleep(0.5)
                self.display_system_health(system_data)
                time.sleep(0.5)
                self.display_network_activity(pihole_data)
                
                # Wait for next update
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            print("\nShutting down monitor...")
        finally:
            self.piglow.all(0)
            print("All LEDs turned off. Goodbye!")

# Additional utility functions
def test_pihole_connection():
    """Test if Pi-hole API is accessible"""
    try:
        response = requests.get("http://localhost/admin/api.php", timeout=5)
        if response.status_code == 200:
            print("✓ Pi-hole API accessible")
            return True
        else:
            print("✗ Pi-hole API returned error")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to Pi-hole API: {e}")
        return False

def test_piglow_hardware():
    """Test PiGlow hardware"""
    try:
        piglow = PiGlow()
        print("✓ PiGlow hardware accessible")
        
        # Quick test
        piglow.all(50)
        time.sleep(1)
        piglow.all(0)
        return True
    except Exception as e:
        print(f"✗ PiGlow hardware error: {e}")
        return False

def quick_status_check():
    """Quick one-time status display"""
    monitor = PiHolePiGlowMonitor()
    
    if not test_pihole_connection():
        print("Please ensure Pi-hole is running and accessible")
        return
    
    if not test_piglow_hardware():
        print("Please check PiGlow hardware connection")
        return
    
    pihole_data = monitor.get_pihole_status()
    system_data = monitor.get_system_metrics()
    
    # Show status for 10 seconds
    monitor.display_pihole_status(pihole_data)
    monitor.display_system_health(system_data)
    monitor.display_network_activity(pihole_data)
    
    print("Status displayed for 10 seconds...")
    time.sleep(10)
    monitor.piglow.all(0)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Quick test mode
            quick_status_check()
        elif sys.argv[1] == "check":
            # Check dependencies
            print("Checking system requirements...")
            test_pihole_connection()
            test_piglow_hardware()
        else:
            print("Usage: python3 pihole_monitor.py [test|check]")
    else:
        # Full monitoring mode
        monitor = PiHolePiGlowMonitor()
        
        # Test connection first
        if test_pihole_connection() and test_piglow_hardware():
            monitor.run_monitor()
        else:
            print("Cannot start monitor - check Pi-hole and PiGlow")
            sys.exit(1)