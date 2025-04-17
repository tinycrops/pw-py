import os
import time
import threading
from glob import glob
from .gemini_client import GeminiClient
from .video_recorder import VideoRecorder

RECORDINGS_DIR = 'recordings'
VIDEO_SUFFIX = '.mp4'
SCREEN_SUFFIX = '_screen.mp4'
ANALYSIS_SUFFIX = '_analysis.json'

def expand_context_if_needed(analysis, screen_path):
    print(f"[Agent] Expanding context with screen: {screen_path}")
    # TODO: Analyze screen recording if needed
    # TODO: Query conversation state
    # TODO: Call research tools (web search, etc.)
    return {"screen_analysis": "Mock screen analysis."}

class AgentOrchestrator:
    def __init__(self, api_key=None):
        self.gemini = GeminiClient(api_key=api_key)
        self.processed = set()

    def watch_recordings(self):
        print("[Agent] Watching for new recordings...")
        while True:
            video_files = glob(os.path.join(RECORDINGS_DIR, 'recording_*.mp4'))
            for video_file in video_files:
                if video_file.endswith(SCREEN_SUFFIX):
                    continue  # Skip screen recordings here
                base = video_file[:-len(VIDEO_SUFFIX)]
                screen_file = base + SCREEN_SUFFIX
                analysis_file = base + ANALYSIS_SUFFIX
                if analysis_file in self.processed:
                    continue
                if not os.path.exists(screen_file):
                    continue  # Wait for screen recording to exist
                print(f"[Agent] Found new video: {video_file} with screen: {screen_file}")
                analysis = self.gemini.analyze_video(video_file)
                context = expand_context_if_needed(analysis, screen_file)
                # Save analysis
                with open(analysis_file, 'w') as f:
                    import json
                    json.dump({"analysis": analysis, "context": context}, f, indent=2)
                self.processed.add(analysis_file)
            time.sleep(2)

def main():
    # Start the video recorder hotkey listener in a background thread
    recorder = VideoRecorder()
    recorder_thread = threading.Thread(target=recorder.hotkey_listener, daemon=True)
    recorder_thread.start()

    orchestrator = AgentOrchestrator()
    watch_thread = threading.Thread(target=orchestrator.watch_recordings)
    watch_thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Exiting agent orchestrator.')

if __name__ == '__main__':
    main() 