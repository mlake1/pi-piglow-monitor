#!/usr/bin/env python3
"""
Simple PiGlow Test Script
Tests basic PiGlow functionality to ensure hardware is working correctly.

Usage: python3 simple_test.py
"""

import time
import sys

try:
    from piglow import PiGlow
except ImportError:
    print("❌ Error: PiGlow library not installed")
    print("Install with: sudo pip3 install piglow")
    sys.exit(1)

def test_piglow():
    """Run basic PiGlow hardware tests"""
    print("🔴 PiGlow Hardware Test Starting...")
    print("This will test all LEDs and basic functionality")
    print("Press Ctrl+C to stop at any time\n")
    
    try:
        piglow = PiGlow()
        print("✅ PiGlow object created successfully")
        
        # Test 1: All LEDs on/off
        print("\n🧪 Test 1: All LEDs on/off")
        piglow.all(100)
        print("   All LEDs should be bright")
        time.sleep(2)
        piglow.all(0)
        print("   All LEDs should be off")
        time.sleep(1)
        
        # Test 2: Individual colors
        print("\n🧪 Test 2: Individual colors")
        colors = ['red', 'orange', 'yellow', 'green', 'blue', 'white']
        for color in colors:
            print(f"   Testing {color} LEDs")
            piglow.color(color, 100)
            time.sleep(0.8)
            piglow.color(color, 0)
            time.sleep(0.2)
        
        # Test 3: Individual arms
        print("\n🧪 Test 3: Individual arms")
        for arm in range(3):
            print(f"   Testing arm {arm}")
            piglow.arm(arm, 100)
            time.sleep(0.8)
            piglow.arm(arm, 0)
            time.sleep(0.2)
        
        # Test 4: Brightness levels
        print("\n🧪 Test 4: Brightness levels")
        print("   Testing brightness fade")
        for brightness in range(0, 101, 10):
            piglow.all(brightness)
            time.sleep(0.1)
        
        for brightness in range(100, -1, -10):
            piglow.all(brightness)
            time.sleep(0.1)
        
        # Test 5: Individual LEDs
        print("\n🧪 Test 5: Individual LEDs")
        print("   Testing each LED individually")
        for led in range(18):
            piglow.led(led, 100)
            time.sleep(0.1)
            piglow.led(led, 0)
        
        # Success pattern
        print("\n🎉 All tests completed successfully!")
        print("   Playing success pattern...")
        
        # Rainbow success pattern
        for _ in range(3):
            for color in colors:
                piglow.color(color, 80)
                time.sleep(0.2)
                piglow.color(color, 0)
        
        print("✅ PiGlow hardware is working correctly!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Check PiGlow is properly connected to GPIO pins")
        print("   2. Ensure I2C is enabled: sudo raspi-config")
        print("   3. Check I2C device: sudo i2cdetect -y 1")
        print("   4. Verify user permissions for I2C access")
        return False
    
    finally:
        try:
            piglow.all(0)
        except:
            pass
    
    return True

def test_i2c():
    """Test I2C connectivity"""
    print("\n🔍 Testing I2C connectivity...")
    
    try:
        import subprocess
        result = subprocess.run(['i2cdetect', '-y', '1'], 
                              capture_output=True, text=True)
        
        if '54' in result.stdout:
            print("✅ PiGlow detected on I2C bus (address 0x54)")
            return True
        else:
            print("❌ PiGlow not detected on I2C bus")
            print("🔧 Check connections and ensure I2C is enabled")
            return False
            
    except FileNotFoundError:
        print("❌ i2cdetect command not found")
        print("   Install with: sudo apt install i2c-tools")
        return False
    except Exception as e:
        print(f"❌ I2C test failed: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 50)
    print("PiGlow Hardware Test")
    print("=" * 50)
    
    # Test I2C first
    if not test_i2c():
        return False
    
    # Test PiGlow
    if not test_piglow():
        return False
    
    print("\n" + "=" * 50)
    print("🎊 All tests passed! Your PiGlow is ready to use.")
    print("=" * 50)
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        try:
            piglow = PiGlow()
            piglow.all(0)
        except:
            pass
        sys.exit(0)