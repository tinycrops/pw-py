import os
import json
from google import genai
from google.genai import types

DEFAULT_PROMPT = """# DEFAULT_PROMPT: Video Analysis Prompt

**Prompt Location:** [video-watcher/server/video-processor.mjs](//starter-applets/video-watcher/server/video-processor.mjs#L13)

---

```
Analyze this video recording and provide a detailed description of:
1. The content visible on the screen
2. Any actions or activities being performed
3. Key topics discussed or shown
4. Transcribe any spoken content with timestamps.

Structure your response as a JSON object with the following fields:
{
  "summary": "Detailed summary of the video",
  "screenContent": "Description of what's visible on the screen",
  "actions": "Description of actions performed",
  "topics": ["topic1", "topic2"],
  "transcript": [{"time_stamp": "HH:MM:SS", "text": "Transcription of spoken content"}],
  "tags": ["tag1", "tag2"]
}
```
"""

PROCESSED_VIDEOS_FILE = "processed_videos.txt"
PROCESSED_RESULTS_DIR = "recordings"

def load_processed_videos():
    if not os.path.exists(PROCESSED_VIDEOS_FILE):
        return set()
    with open(PROCESSED_VIDEOS_FILE, "r") as f:
        return set(f.read().splitlines())

def add_processed_video(video_path):
    processed_videos = load_processed_videos()
    processed_videos.add(video_path)
    with open(PROCESSED_VIDEOS_FILE, "w") as f:
        f.write("\n".join(processed_videos))

def get_analysis_filepath(video_path):
    """Generates the expected analysis JSON file path for a given video path."""
    # Use a simple approach: replace slashes with underscores and append .json
    filename = os.path.basename(video_path).replace('/', '_').replace('\\', '_')
    return os.path.join(PROCESSED_RESULTS_DIR, f"{filename}.json")

def load_analysis_result(video_path):
    """Loads the saved analysis result for a given video path."""
    analysis_filepath = get_analysis_filepath(video_path)
    if os.path.exists(analysis_filepath):
        try:
            with open(analysis_filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading analysis from {analysis_filepath}: {e}")
    return None

class GeminiClient:
    def __init__(self, api_key=None, model_name="gemini-2.0-flash"):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set and no api_key provided.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def analyze_video(self, video_path, prompt=DEFAULT_PROMPT):
        processed_videos = load_processed_videos()
        if video_path in processed_videos:
            print(f"Video already processed: {video_path}")
            # Instead of returning a placeholder, load and return the actual analysis
            existing_analysis = load_analysis_result(video_path)
            if existing_analysis:
                print(f"Loaded existing analysis for {video_path}")
                return existing_analysis
            else:
                # If we can't load the analysis, return a more informative message
                video_name = os.path.basename(video_path)
                return {
                    "status": "already_analyzed",
                    "summary": f"This video ({video_name}) was already analyzed, but the analysis data couldn't be loaded.",
                    "topics": ["video analysis"],
                    "tags": ["processed"],
                    "screenContent": "Content not available for already processed video.",
                    "actions": "Actions not available for already processed video.",
                    "transcript": []
                }

        # Upload the video file
        video_file = self.client.files.upload(file=video_path)
        # Wait for processing
        import time
        while video_file.state == "PROCESSING":
            print(f"Waiting for video to be processed: {video_path}")
            time.sleep(5)
            video_file = self.client.files.get(name=video_file.name)
        if video_file.state == "FAILED":
            raise RuntimeError(f"Video processing failed for {video_path}")

        # Prepare structured content
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=video_file.uri,
                        mime_type=video_file.mime_type,
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )

        # Generate content and collect the full response
        response_chunks = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=generate_content_config,
        )
        full_response = ""
        for chunk in response_chunks:
            full_response += chunk.text
        try:
            result = json.loads(full_response)
            add_processed_video(video_path)
            # Save the analysis result to a JSON file
            os.makedirs(PROCESSED_RESULTS_DIR, exist_ok=True)
            analysis_filepath = get_analysis_filepath(video_path)
            with open(analysis_filepath, "w") as f:
                json.dump(result, f, indent=4)
            return result
        except Exception as e:
            print(f"Failed to parse Gemini response as JSON: {e}\nRaw response: {full_response}")
            return {"raw_response": full_response}

    def send_text_prompt(self, prompt_text, history=None):
        """Sends a text prompt to the configured Gemini model."""
        try:
            contents = []
            if history:
                for item in history:
                    contents.append(types.Content(role=item['role'], parts=[types.Part.from_text(text=item['text'])]))

            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)]))

            # For simple text prompts, we don't necessarily need JSON response mime type
            # generate_content_config = types.GenerateContentConfig(
            #     response_mime_type="text/plain", # Or leave as default
            # )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                # config=generate_content_config,
            )
            # Assuming the response has a 'text' attribute
            return {"text": response.text}
        except Exception as e:
            print(f"Error sending text prompt to Gemini: {e}")
            return {"error": str(e)} 