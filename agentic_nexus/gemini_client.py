import os
import json
from google import genai
from google.genai import types

DEFAULT_PROMPT = """Analyze this video recording and provide a detailed description of: 1. The content visible on the screen 2. Any actions or activities being performed 3. Key topics discussed or shown 4. Transcribe any spoken content  Structure your response as a JSON object with the following fields: {   'summary': 'Detailed summary of the video',   'screenContent': 'Description of what's visible on the screen',   'actions': 'Description of actions performed',   'topics': ['topic1', 'topic2'],   'transcript': 'Transcription of speech',   'tags': ['tag1', 'tag2'] }"""

class GeminiClient:
    def __init__(self, api_key=None, model_name="gemini-2.0-flash"):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set and no api_key provided.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def analyze_video(self, video_path, prompt=DEFAULT_PROMPT):
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

        # Prepare structured content and schema
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
        response_schema = genai.types.Schema(
            type=genai.types.Type.OBJECT,
            properties={
                "summary": genai.types.Schema(type=genai.types.Type.STRING),
                "screenContent": genai.types.Schema(type=genai.types.Type.STRING),
                "actions": genai.types.Schema(type=genai.types.Type.STRING),
                "topics": genai.types.Schema(type=genai.types.Type.ARRAY, items=genai.types.Schema(type=genai.types.Type.STRING)),
                "transcript": genai.types.Schema(type=genai.types.Type.STRING),
                "tags": genai.types.Schema(type=genai.types.Type.ARRAY, items=genai.types.Schema(type=genai.types.Type.STRING)),
            },
        )
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
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
            return json.loads(full_response)
        except Exception as e:
            print(f"Failed to parse Gemini response as JSON: {e}\nRaw response: {full_response}")
            return {"raw_response": full_response} 