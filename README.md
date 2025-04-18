# Video Journal Assistant

A personal video journal application that uses AI to analyze your recorded videos and maintain a conversation with you about their content. The application allows you to record videos from your webcam with a single keystroke (F9) and then automatically processes them to extract insights, summaries, and transcripts.

## Features

- Record videos from your webcam with a single keystroke (F9)
- Automatic video processing with Google's Gemini API
- Conversation with an AI assistant that maintains context about your videos
- Simple, clean UI that displays video summaries and the assistant's responses

## Requirements

- Python 3.9+
- Node.js 16+ and npm
- ffmpeg (for video recording)
- A Gemini API key from Google AI Studio

## Setup

1. Clone this repository
   ```
   git clone https://github.com/yourusername/video-journal-assistant.git
   cd video-journal-assistant
   ```

2. Install Python dependencies
   ```
   pip install -r requirements.txt
   ```

3. Install frontend dependencies
   ```
   cd ui/frontend
   npm install
   cd ../..
   ```

4. Set up your Gemini API key
   ```
   export GEMINI_API_KEY="your_api_key_here"
   ```

5. Start the application
   ```
   ./start_app.sh
   ```

## Usage

1. The application will open in your browser at http://localhost:5173
2. Press F9 to start recording a video from your webcam
3. Press F9 again to stop recording
4. The AI will automatically process the video and show you a summary
5. Continue recording videos, and the AI will maintain context between sessions

## Directory Structure

- `/agentic_nexus` - Core backend components (video recording, AI agent)
- `/ui/backend` - Flask backend API
- `/ui/frontend` - React frontend application
- `/recordings` - Where your videos and their analyses are stored

## How It Works

1. The video recorder captures both your webcam feed and screen when you press F9
2. When you press F9 again, the recording stops and is saved to the `/recordings` directory
3. The application automatically sends the video to the Gemini API for analysis
4. The AI agent maintains a conversation state that tracks all of your videos
5. The agent uses function calling to retrieve information about your videos as needed

## Troubleshooting

- If the webcam doesn't work, make sure ffmpeg is installed and that your webcam is not being used by another application
- If you get API errors, check that your Gemini API key is correctly set
- Videos are stored in the `/recordings` directory. If you run out of disk space, you can delete older videos

## License

MIT 