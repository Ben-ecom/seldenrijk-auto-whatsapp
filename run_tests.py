"""
Test Runner Script

Dit script draait alle tests in de juiste volgorde en genereert een rapport.

Usage:
    python run_tests.py              # Draai alle tests
    python run_tests.py --unit       # Alleen unit tests
    python run_tests.py --integration # Alleen integration tests
    python run_tests.py --quick      # Snelle tests (geen slow tests)
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Draai een command en print resultaat."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, shell=True)

    if result.returncode == 0:
        print(f"\n✅ {description} geslaagd!")
        return True
    else:
        print(f"\n❌ {description} gefaald!")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test runner voor WhatsApp Recruitment Platform")
    parser.add_argument("--unit", action="store_true", help="Draai alleen unit tests")
    parser.add_argument("--integration", action="store_true", help="Draai alleen integration tests")
    parser.add_argument("--e2e", action="store_true", help="Draai alleen e2e tests")
    parser.add_argument("--rag", action="store_true", help="Draai alleen RAG tests")
    parser.add_argument("--quick", action="store_true", help="Draai alleen snelle tests")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Base pytest command
    pytest_cmd = "python -m pytest"

    if args.verbose:
        pytest_cmd += " -vv"

    # Test selectie
    if args.unit:
        pytest_cmd += " -m unit"
    elif args.integration:
        pytest_cmd += " -m integration"
    elif args.e2e:
        pytest_cmd += " -m e2e"
    elif args.rag:
        pytest_cmd += " -m rag"
    elif args.quick:
        pytest_cmd += " -m 'not slow'"

    print("\n" + "="*60)
    print("🚀 WhatsApp Recruitment Platform - Test Suite")
    print("="*60)

    # Check of pytest is geïnstalleerd
    try:
        subprocess.run(["python", "-m", "pytest", "--version"], check=True, capture_output=True)
    except:
        print("\n❌ pytest niet gevonden. Installeer met: pip install pytest pytest-asyncio")
        sys.exit(1)

    # Draai tests
    all_passed = True

    if not any([args.unit, args.integration, args.e2e, args.rag]):
        # Draai alle test suites in volgorde
        print("\n📋 Draai complete test suite...")

        # 1. Unit tests voor Agent 1
        if not run_command(
            "python tests/test_agent_1.py",
            "Agent 1 Unit Tests"
        ):
            all_passed = False

        # 2. Unit tests voor Agent 2
        if not run_command(
            "python tests/test_agent_2.py",
            "Agent 2 Unit Tests"
        ):
            all_passed = False

        # 3. RAG tests
        if not run_command(
            "python tests/test_rag.py",
            "RAG Accuracy Tests"
        ):
            all_passed = False

        # 4. API integration tests
        print("\n⚠️  Voor API tests: zorg dat server draait met 'python -m api.main'")
        input("   Druk op Enter om door te gaan...")

        if not run_command(
            "python tests/test_api.py",
            "API Integration Tests"
        ):
            all_passed = False

        # 5. End-to-end orchestratie tests
        if not run_command(
            "python tests/test_orchestration.py",
            "End-to-End Orchestratie Tests"
        ):
            all_passed = False

    else:
        # Draai geselecteerde tests met pytest
        if not run_command(pytest_cmd, "Geselecteerde Tests"):
            all_passed = False

    # Samenvatting
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALLE TESTS GESLAAGD!")
        print("="*60)
        sys.exit(0)
    else:
        print("❌ SOMMIGE TESTS GEFAALD")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()
