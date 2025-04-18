from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os
import threading
import json
from datetime import datetime

# Add the parent directory (pw-py) to the Python path
# to allow importing from agentic_nexus
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(os.path.dirname(parent_dir))

# Now we can import from agentic_nexus
from agentic_nexus.video_recorder import VideoRecorder
from agentic_nexus.agent import VideoAgent
from agentic_nexus.memory_manager import get_memory_manager
from agentic_nexus.gemini_client import GeminiClient, load_analysis_result, get_analysis_filepath

app = Flask(__name__)
# Enable CORS for all routes and all origins (for development)
CORS(app)

# Initialize the VideoAgent
agent = VideoAgent()

# Initialize video recorder
recorder = VideoRecorder()
is_recording = False

# Directory where recordings are stored
RECORDINGS_DIR = 'recordings'

# Initialize agent with initial context at startup
def initialize_agent():
    """Initialize the agent with available videos and memory at startup."""
    print("Initializing agent with existing videos and memory...")
    
    # Create recordings directory if it doesn't exist
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    
    # Load existing videos
    if os.path.exists(RECORDINGS_DIR):
        # First, get all .mp4 files that have corresponding .json analysis files
        video_files = []
        for file in os.listdir(RECORDINGS_DIR):
            if file.endswith('.mp4') and not file.endswith('_screen.mp4'):
                json_file = file.replace('.mp4', '.json')
                if os.path.exists(os.path.join(RECORDINGS_DIR, json_file)):
                    video_files.append((os.path.join(RECORDINGS_DIR, file), os.path.join(RECORDINGS_DIR, json_file)))
        
        # Sort by modification time, newest last (so memory builds chronologically)
        video_files.sort(key=lambda x: os.path.getmtime(x[0]))
        
        # Add each video analysis to the agent in chronological order
        for video_path, json_path in video_files:
            try:
                with open(json_path, 'r') as f:
                    video_analysis = json.load(f)
                    
                    # Add timestamp if not present
                    if 'timestamp' not in video_analysis:
                        timestamp = datetime.fromtimestamp(os.path.getmtime(video_path)).strftime('%Y-%m-%d %H:%M:%S')
                        video_analysis['timestamp'] = timestamp
                    
                    # Add to the agent's memory
                    agent.add_video_to_context(video_analysis)
                    print(f"Loaded video analysis: {os.path.basename(json_path)}")
            except Exception as e:
                print(f"Error loading video analysis {json_path}: {e}")
    
    # Generate an initial response from the agent
    if agent.conversation_state:
        try:
            # Query the agent about the available videos
            response = agent.process_user_input("What videos do I have available? Provide a brief summary of each.")
            print(f"Initial agent context summary: {response}")
        except Exception as e:
            print(f"Error generating initial agent response: {e}")

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns the current status (e.g., recording state)."""
    global is_recording
    return jsonify({
        "is_recording": is_recording,
        "processed_video_count": len(agent.conversation_state)
    })

@app.route('/api/conversation', methods=['GET'])
def get_conversation():
    """Returns the current conversation state."""
    # Get memory context for additional information
    memory_manager = get_memory_manager()
    memory_context = memory_manager.get_memory_context()
    
    return jsonify({
        "history": agent.message_history,
        "videos": agent.conversation_state,
        "memory_context": memory_context
    })

@app.route('/api/toggle_recording', methods=['POST'])
def toggle_recording():
    """Start or stop recording."""
    global is_recording
    
    if is_recording:
        # Stop recording
        recorder.stop()
        is_recording = False
        
        # Process the latest recording in a background thread
        latest_recording = _get_latest_recording()
        if latest_recording:
            threading.Thread(target=_process_recording, args=(latest_recording,)).start()
            return jsonify({"message": f"Recording stopped. Processing {latest_recording}"})
        else:
            return jsonify({"error": "No recording found to process"})
    else:
        # Start recording
        recorder.start()
        is_recording = True
        return jsonify({"message": "Recording started"})

@app.route('/api/agent_query', methods=['POST'])
def agent_query():
    """Process a user query to the agent."""
    data = request.json
    user_query = data.get('query')
    
    # Process with the agent (it will handle empty queries by showing video summaries)
    response = agent.process_user_input(user_query)
    
    return jsonify({"response": response})

@app.route('/api/latest_video_info', methods=['GET'])
def latest_video_info():
    """Get information about the latest video for agent display."""
    if agent.conversation_state:
        # Get the most recent video from the conversation state
        latest_video = agent.conversation_state[-1]
        
        # Skip status messages
        if isinstance(latest_video, dict) and latest_video.get("status") == "skipped":
            return jsonify({
                "message": "No new video analysis available",
                "memory_context": get_memory_manager().get_memory_context()
            })
            
        # Process with the agent to get analysis details
        response = agent.process_user_input("What's new in my latest video?")
        return jsonify({
            "video": latest_video,
            "agent_analysis": response,
            "memory_context": get_memory_manager().get_memory_context()
        })
    else:
        return jsonify({
            "message": "No videos available yet"
        })

@app.route('/api/memory', methods=['GET'])
def get_memory():
    """Get the current memory state."""
    memory_manager = get_memory_manager()
    return jsonify({
        "short_term_memory": memory_manager.short_term_memory,
        "working_memory": memory_manager.working_memory,
        "long_term_memory": memory_manager.long_term_memory
    })

def _get_latest_recording():
    """Get the path to the latest recording."""
    if not os.path.exists(RECORDINGS_DIR):
        return None
    video_files = [f for f in os.listdir(RECORDINGS_DIR) if f.endswith('.mp4') and not f.endswith('_screen.mp4')]
    if not video_files:
        return None
    
    # Sort by creation/modification time to get the most recently created file
    latest_file = max(video_files, key=lambda f: os.path.getmtime(os.path.join(RECORDINGS_DIR, f)))
    latest_path = os.path.join(RECORDINGS_DIR, latest_file)
    
    # Make sure the file exists and is complete (not still being written)
    # Wait a short time to ensure recording is complete
    import time
    time.sleep(1.0)  # Wait 1 second to ensure file is closed
    
    if os.path.exists(latest_path):
        # Check if file size is stable (not still being written)
        initial_size = os.path.getsize(latest_path)
        time.sleep(0.5)  # Wait a bit more
        current_size = os.path.getsize(latest_path)
        
        if initial_size == current_size:
            return latest_path
        else:
            print(f"File {latest_path} is still being written, waiting...")
            # Wait for file size to stabilize
            max_attempts = 10
            for _ in range(max_attempts):
                time.sleep(1.0)
                new_size = os.path.getsize(latest_path)
                if new_size == current_size:
                    return latest_path
                current_size = new_size
            
            print(f"Warning: File size still changing after {max_attempts} attempts")
            # Return the file anyway, we've waited long enough
            return latest_path
    
    return None

def _process_recording(recording_path):
    """Process a recording using the Gemini client and update the agent's state."""
    try:
        # Check if the file exists and has a non-zero size
        if not os.path.exists(recording_path) or os.path.getsize(recording_path) == 0:
            print(f"Error: Recording file {recording_path} doesn't exist or is empty")
            return
            
        # Check if this recording has already been processed
        existing_result = load_analysis_result(recording_path)
        if existing_result:
            print(f"Using existing analysis for {recording_path}")
            # Add a meaningful message to the conversation state rather than just skipping
            result = {
                "summary": f"Analysis of video {os.path.basename(recording_path)}",
                "timestamp": datetime.fromtimestamp(os.path.getmtime(recording_path)).strftime('%Y-%m-%d %H:%M:%S'),
                "analysis": existing_result
            }
            # Add the result to the agent's conversation state
            agent.add_video_to_context(result)
            return
            
        # Initialize Gemini client and process the video
        gemini_client = GeminiClient()
        result = gemini_client.analyze_video(recording_path)
        
        # If result indicates "skipped", create a more detailed result
        if isinstance(result, dict) and result.get("status") == "skipped":
            # Try to load existing analysis to provide richer data
            existing_file = get_analysis_filepath(recording_path)
            if os.path.exists(existing_file):
                try:
                    with open(existing_file, 'r') as f:
                        existing_data = json.load(f)
                        result = existing_data
                except Exception:
                    # If loading fails, keep original skipped result
                    pass
        
        # Add timestamp to the result
        timestamp = datetime.fromtimestamp(os.path.getmtime(recording_path)).strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(result, dict):
            result['timestamp'] = timestamp
        
        # Update the agent's conversation state
        agent.add_video_to_context(result)
        
        # Trigger an initial agent query to generate a response about the new video
        initial_response = agent.process_user_input("Tell me about the video I just recorded.")
        print(f"Initial agent response: {initial_response}")
        
        print(f"Successfully processed video: {recording_path}")
    except Exception as e:
        print(f"Error processing video {recording_path}: {e}")
        import traceback
        traceback.print_exc()

def get_analysis_filepath(video_path):
    """Generates the expected analysis JSON file path for a given video path."""
    # Use a simple approach: replace slashes with underscores and append .json
    filename = os.path.basename(video_path).replace('/', '_').replace('\\', '_')
    return os.path.join(RECORDINGS_DIR, f"{filename}.json")

# Add a keyboard listener for F9 to toggle recording
def start_keyboard_listener():
    """Start the keyboard listener for F9 to toggle recording."""
    # Disable backend keyboard listener as we're using the frontend one
    # threading.Thread(target=recorder.hotkey_listener, daemon=True).start()
    pass  # Do nothing, letting the frontend handle the F9 key

if __name__ == '__main__':
    # Start the keyboard listener
    start_keyboard_listener()
    
    # Initialize the agent with existing videos
    initialize_agent()
    
    # Run the Flask app
    app.run(debug=True, port=5001) 