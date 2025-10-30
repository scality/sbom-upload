#!/usr/bin/env python3
"""Test script for version comparison functions"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from domain.version import (
    is_latest_version, 
    get_latest_version, 
    compare_versions
)

def test_version_functions():
    """Test the version comparison functions"""
    
    print("🧪 Testing Version Functions")
    print("=" * 50)
    
    # Test data
    versions = ["1.0.0", "2.0.0", "1.5.0", "2.1.0-beta", "2.1.0", "3.0.0-alpha"]
    
    print(f"📋 Test versions: {versions}")
    print()
    
    # Test get_latest_version
    latest = get_latest_version(versions)
    print(f"🏆 Latest version: {latest}")
    
    # Test is_latest_version
    test_cases = [
        ("2.1.0", versions),
        ("3.0.0-alpha", versions),
        ("1.0.0", versions),
        ("3.1.0", versions),  # Not in list but newer
        ("0.9.0", versions),  # Not in list and older
    ]
    
    print("🔍 Testing is_latest_version:")
    for version, version_list in test_cases:
        is_latest = is_latest_version(version, version_list)
        status = "✅ IS LATEST" if is_latest else "❌ NOT LATEST"
        print(f"  {version:12} -> {status}")
    
    print()
    
    # Test specific comparisons
    print("🔄 Testing specific comparisons:")
    comparisons = [
        ("2.1.0", "2.1.0-beta"),
        ("3.0.0", "3.0.0-alpha"),
        ("1.0.0", "2.0.0"),
        ("v2.1.0", "2.1.0"),  # With 'v' prefix
    ]
    
    for v1, v2 in comparisons:
        result = compare_versions(v1, v2)
        if result > 0:
            comparison = f"{v1} > {v2}"
        elif result < 0:
            comparison = f"{v1} < {v2}"
        else:
            comparison = f"{v1} = {v2}"
        print(f"  {comparison}")

if __name__ == "__main__":
    test_version_functions()
