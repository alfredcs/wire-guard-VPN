#!/bin/bash
#
# Run VPN Server Tests
# Quick script to run the test suite
#

set -e

echo "================================"
echo "VPN Server Test Suite"
echo "================================"
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found"
    echo "Run: python3 -m venv venv && source venv/bin/activate && pip install -r server/requirements.txt pytest pytest-cov httpx"
    exit 1
fi

# Set Python path
export PYTHONPATH=/codes/vpn/server:$PYTHONPATH

# Parse arguments
COVERAGE=""
VERBOSE="-v"
PATTERN="tests/"

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE="--cov=server/auth_service --cov-report=term-missing"
            shift
            ;;
        --quiet|-q)
            VERBOSE="-q"
            shift
            ;;
        --pattern|-p)
            PATTERN="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --coverage, -c    Run with coverage report"
            echo "  --quiet, -q       Quiet output"
            echo "  --pattern, -p     Test pattern (default: tests/)"
            echo "  --help, -h        Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                          # Run all tests"
            echo "  $0 --coverage               # Run with coverage"
            echo "  $0 -p tests/test_auth.py    # Run specific file"
            exit 0
            ;;
        *)
            PATTERN="$1"
            shift
            ;;
    esac
done

# Run tests
echo "Running tests: $PATTERN"
echo ""
pytest $PATTERN $VERBOSE $COVERAGE

echo ""
echo "================================"
echo "Tests completed successfully!"
echo "================================"
