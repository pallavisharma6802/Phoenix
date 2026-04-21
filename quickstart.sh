#!/bin/bash
# Project Phoenix: Quick Start Script
# Run this to set up and test Phoenix in 2 minutes

set -e

echo ""
echo "=================================================="
echo "Project Phoenix: Quick Start Setup"
echo "=================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check Python
echo -e "${BLUE}[1/5]${NC} Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

# Step 2: Install dependencies
echo ""
echo -e "${BLUE}[2/5]${NC} Installing dependencies..."
pip install -q -r requirements.txt
echo -e "${GREEN}✓${NC} Dependencies installed"

# Step 3: Create logs directory
echo ""
echo -e "${BLUE}[3/5]${NC} Setting up directories..."
mkdir -p /tmp/phoenix
touch /tmp/phoenix_app.log
echo -e "${GREEN}✓${NC} Directories ready"

# Step 4: Run demo
echo ""
echo -e "${BLUE}[4/5]${NC} Running interactive demo..."
echo "  (This will show Phoenix fixing a simulated error)"
echo ""
python3 main.py demo > /tmp/phoenix_demo_output.txt 2>&1
echo ""
echo -e "${GREEN}✓${NC} Demo completed"
echo ""

# Step 5: Show metrics
echo -e "${BLUE}[5/5]${NC} Running test scenarios (this takes ~30 seconds)..."
echo "  (Running 50 incident scenarios to show metrics)"
echo ""
python3 main.py test --scenarios 50 > /tmp/phoenix_test_output.txt 2>&1
echo ""
echo -e "${GREEN}✓${NC} Tests completed"

# Show results
echo ""
echo "=================================================="
echo "QUICK START COMPLETE!"
echo "=================================================="
echo ""
echo -e "${GREEN}✓ Phoenix is ready to use${NC}"
echo ""
echo "Next Steps:"
echo ""
echo "1. View demo results:"
echo "   cat /tmp/phoenix_demo_output.txt | tail -30"
echo ""
echo "2. View test metrics:"
echo "   cat /tmp/phoenix_test_output.txt | tail -40"
echo ""
echo "3. Read the documentation:"
echo "   - Overview: cat README.md"
echo "   - For Founders: cat FOUNDER_REVIEW.md"
echo "   - Deep Dive: cat AGNOST_INTEGRATION.md"
echo ""
echo "4. Try modes:"
echo "   - Interactive Demo: python3 main.py demo"
echo "   - Test Suite: python3 main.py test --scenarios 50"
echo "   - Monitor Mode: python3 main.py monitor --duration 60"
echo ""
echo "=================================================="
echo ""
