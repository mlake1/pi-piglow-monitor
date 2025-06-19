#!/usr/bin/env python3
"""
Pi-hole API Test Script
Tests Pi-hole API connectivity and data retrieval for the PiGlow monitor.

Usage: python3 api_test.py
"""

import requests
import json
import sys
from datetime import datetime

def test_basic_api():
    """Test basic Pi-hole API connectivity"""
    print("🔍 Testing basic Pi-hole API...")
    
    try:
        url = "http://localhost/admin/api.php"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Basic API accessible")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Domains blocked: {data.get('domains_being_blocked', 'N/A')}")
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Pi-hole API")
        print("   Check that Pi-hole is running and accessible")
        return False
    except requests.exceptions.Timeout:
        print("❌ API request timed out")
        return False
    except json.JSONDecodeError:
        print("❌ Invalid JSON response from API")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_summary_api():
    """Test Pi-hole summary API"""
    print("\n🔍 Testing Pi-hole summary API...")
    
    try:
        url = "http://localhost/admin/api.php?summaryRaw"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Summary API accessible")
            