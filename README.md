# Video Journal Assistant

A smart AI assistant that analyzes your screen recordings, builds persistent memory of your activities, and provides personalized insights over time.

## Overview

Video Journal Assistant captures and analyzes your screen recordings, building a persistent memory of your activities, preferences, and patterns. The system combines video analysis with a multi-tiered memory architecture to create an increasingly personalized AI assistant that understands your work context without requiring constant explicit instructions.

## Key Features

- **F9 Recording Toggle**: Press F9 to start/stop screen recording
- **AI Video Analysis**: Automatic content analysis with Gemini 2.0
- **Persistent Memory System**: Three-tiered memory architecture:
  - **Short-Term Memory (STM)**: Recent observations and interactions
  - **Working Memory (WM)**: Current session context and evidence-based hypotheses
  - **Long-Term Memory (LTM)**: Persistent user profile with skills, preferences, and patterns
- **Agent Consciousness**: Personalized responses based on accumulated knowledge about you
- **Interactive UI**: View videos, access agent insights, and see memory context

## Architecture

The system consists of:

1. **Backend** (Flask API):
   - Video recording management
   - Gemini API integration for video analysis
   - Memory management system
   - Agent orchestration

2. **Frontend** (React):
   - Recording controls (F9 toggle)
   - Video listing and querying interface
   - Agent response display
   - Memory context visualization

3. **Memory System**:
   - Hypothesis promotion/demotion based on evidence
   - Persistent storage of user patterns and preferences
   - Context-aware response generation

## Installation

### Prerequisites

- Python 3.8+
- Node.js 14+
- Google Gemini API key

### Setup

1. **Clone the repository**:
   ```
   git clone https://github.com/your-username/video-journal-assistant.git
   cd video-journal-assistant
   ```

2. **Backend setup**:
   ```
   pip install -r requirements.txt
   export GEMINI_API_KEY=your_api_key_here
   ```

3. **Frontend setup**:
   ```
   cd ui/frontend
   npm install
   ```

## Usage

1. **Start the backend**:
   ```
   python -m ui.backend.app
   ```

2. **Start the frontend**:
   ```
   cd ui/frontend
   npm run dev
   ```

3. **Open the application** in your browser (typically at http://localhost:5173)

4. **Record and analyze videos**:
   - Press F9 to start recording
   - Press F9 again to stop recording and trigger analysis
   - View the agent's insights in the interface
   - Click on video cards to get more details about specific recordings

## How It Works

### Recording Process

1. Press F9 to toggle recording state
2. When recording stops, the video is processed by Gemini AI
3. Analysis results are added to the conversation context and memory system
4. Agent generates responses based on the video content and memory context

### Memory System

The system implements a cognitive architecture inspired by human memory:

1. **Short-Term Memory (STM)**
   - Recent video analyses and observations
   - Limited capacity, older entries are removed as new ones are added

2. **Working Memory (WM)**
   - Contains hypotheses at different levels of certainty:
     - Untested hypotheses: New observations needing more evidence
     - Corroborated hypotheses: Observations with moderate support
     - Established facts: Consistently supported observations or explicit statements
   - Hypotheses are promoted or demoted based on accumulated evidence

3. **Long-Term Memory (LTM)**
   - Persistent user profile with categorical organization:
     - Skills and knowledge
     - Preferences and habits
     - Workflows
     - Challenges
     - Goals and motivations
     - Traits and attitudes
   - Updated based on recurring patterns detected in STM

### Agent Personalization

As you use the system, the agent:
1. Builds an understanding of your activities and preferences
2. Provides increasingly personalized responses
3. Focuses on information relevant to your established patterns
4. Proactively offers insights based on your historical context

## Project Structure

```
pw-py/
├── agentic_nexus/
│   ├── agent.py               # AI agent for video analysis
│   ├── gemini_client.py       # Google Gemini API integration
│   ├── memory_manager.py      # Multi-tiered memory system
│   ├── video_recorder.py      # Screen recording functionality
│   └── agent_orchestrator.py  # Coordination between components
├── ui/
│   ├── backend/
│   │   └── app.py             # Flask API server
│   └── frontend/
│       ├── src/               # React frontend code
│       ├── public/            # Static assets
│       └── package.json       # Frontend dependencies
├── recordings/                # Stored videos and analysis results
├── agent_memory/              # Persistent memory storage
├── docs/                      # Documentation for prompts and design
└── README.md                  # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini API for multimodal understanding
- The cognitive science research that inspired the memory architecture 