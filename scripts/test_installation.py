#!/usr/bin/env python3
"""Test script to verify scanner installation."""

import sys
import importlib
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    required_modules = [
        "pydantic",
        "requests",
        "pandas",
        "numpy",
        "streamlit",
        "plotly",
    ]

    optional_modules = [
        "talib",
    ]

    failed = []

    # Test required modules
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module} - REQUIRED")
            failed.append(module)

    # Test optional modules
    for module in optional_modules:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ⚠️  {module} - OPTIONAL (will use pandas fallback)")

    if failed:
        print(f"\n❌ Missing required modules: {', '.join(failed)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("\n✅ All required imports successful!")
    return True


def test_scanner_modules():
    """Test scanner module imports."""
    print("\nTesting scanner modules...")

    scanner_modules = [
        "scanner.core.models",
        "scanner.core.data_providers.base",

        "scanner.core.indicators",
        "scanner.core.strategy",
        "scanner.core.scanner",
        "scanner.config",
        "scanner.integrations.export",
    ]

    failed = []

    for module in scanner_modules:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module}")
        except Exception as e:
            print(f"  ❌ {module}: {e}")
            failed.append(module)

    if failed:
        print(f"\n❌ Failed to import scanner modules: {', '.join(failed)}")
        return False

    print("\n✅ All scanner modules imported successfully!")
    return True


def test_basic_functionality():
    """Test basic scanner functionality."""
    print("\nTesting basic scanner functionality...")

    try:
        from scanner.config import Config



        # Test config
        print("  Testing config loading...")
        config = Config.from_defaults()
        print("  ✅ Config loaded")

        # Test getting a simple quote


        print("\n✅ Basic functionality test passed!")
        return True

    except Exception as e:
        print(f"\n❌ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("📈 Momentum Scanner - Installation Test")
    print("=" * 60)
    print()

    # Check Python version
    print("Checking Python version...")
    version = sys.version_info
    print(f"  Python {version.major}.{version.minor}.{version.micro}")

    if version < (3, 10):
        print("  ❌ Python 3.10 or higher required")
        return False

    print("  ✅ Python version OK")
    print()

    # Run tests
    tests = [
        ("Module Imports", test_imports),
        ("Scanner Modules", test_scanner_modules),
        ("Basic Functionality", test_basic_functionality),
    ]

    results = []
    for name, test_func in tests:
        print()
        success = test_func()
        results.append((name, success))

    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if not success:
            all_passed = False

    print()

    if all_passed:
        print("✅ All tests passed! Your installation is ready.")
        print()
        print("Next steps:")
        print("  1. Edit config.json with your settings")
        print("  2. Run: python -m scanner.modes.cli --symbols AAPL,MSFT")
        print("  3. Or: python scripts/run_ui.py")
        print()
        return True
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
