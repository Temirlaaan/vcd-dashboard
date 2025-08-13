#!/bin/bash

echo "🚀 Starting VCD IP Manager..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed!${NC}"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed!${NC}"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Start Backend
echo -e "${YELLOW}📦 Starting Backend...${NC}"
cd backend

# Check .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found!${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${RED}📝 Please edit backend/.env file with your API tokens!${NC}"
    exit 1
fi

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Start FastAPI in background
echo -e "${GREEN}✅ Starting FastAPI server...${NC}"
python app.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Frontend
cd ../frontend
echo -e "${YELLOW}📦 Starting Frontend...${NC}"

# Install Node dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

# Start React app
echo -e "${GREEN}✅ Starting React development server...${NC}"
npm start &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}✅ VCD IP Manager is running!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔧 API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Function to handle shutdown
shutdown() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}✅ Servers stopped${NC}"
    exit 0
}

# Trap Ctrl+C
trap shutdown INT

# Wait for processes
wait $BACKEND_PID
wait $FRONTEND_PID