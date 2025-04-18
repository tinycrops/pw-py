#!/bin/bash

# Function to kill processes on exit
cleanup() {
    echo "Shutting down services..."
    kill $FRONTEND_PID $BACKEND_PID 2>/dev/null
    exit 0
}

# Set up trap for SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check for required environment variables
if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY environment variable not set."
    echo "Please set it with: export GEMINI_API_KEY=your_api_key"
    exit 1
fi

# Start backend Flask server
echo "Starting backend server..."
cd ui/backend
python app.py &
BACKEND_PID=$!
cd ../..

# Check if backend started successfully
sleep 2
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Error: Backend server failed to start."
    exit 1
fi

# Start frontend development server
echo "Starting frontend server..."
cd ui/frontend
npm run dev &
FRONTEND_PID=$!
cd ../..

# Check if frontend started successfully
sleep 5
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "Error: Frontend server failed to start."
    kill $BACKEND_PID
    exit 1
fi

echo "Both services are running."
echo "Frontend will be available at: http://localhost:5173"
echo "Backend API is at: http://localhost:5001"
echo "Press Ctrl+C to stop all services."

# Wait for both processes
wait $FRONTEND_PID $BACKEND_PID 