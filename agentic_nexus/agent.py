import os
import json
import base64
from google import genai
from google.genai import types
from typing import Dict, List, Any, Optional
from .memory_manager import get_memory_manager

class VideoAgent:
    def __init__(self, api_key=None, model_name="gemini-2.0-flash"):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set and no api_key provided.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.conversation_state = []
        self.message_history = []
        # Initialize the memory manager
        self.memory_manager = get_memory_manager()
    
    def add_video_to_context(self, video_analysis):
        """Add a processed video analysis to the conversation context."""
        # Add to conversation state for backward compatibility
        self.conversation_state.append(video_analysis)
        
        # Add to memory system
        self.memory_manager.add_video_analysis_to_memory(video_analysis)
        
        # Create a summary message for the chat history
        summary = {
            "role": "user", 
            "content": f"A new video was recorded and analyzed. Summary: {video_analysis.get('summary', 'No summary available')}"
        }
        self.message_history.append(summary)
        
        # Add a system message about memory context
        memory_context = self.memory_manager.get_memory_context()
        memory_msg = {
            "role": "user",
            "content": f"Based on your memory, you now know: {json.dumps(memory_context, indent=2)}"
        }
        self.message_history.append(memory_msg)
        
    def clear_conversation_state(self):
        """Clear the conversation state and message history."""
        self.conversation_state = []
        self.message_history = []
        
    def _build_system_prompt(self):
        """Build the system prompt for the agent."""
        # Get memory context to personalize the prompt
        memory_context = self.memory_manager.get_memory_context()
        
        base_prompt = """You are a helpful AI assistant that helps the user by analyzing their recorded videos.
You have access to information about videos the user has recorded.
Use the getVideoInfo function to retrieve information about specific videos.
If no specific video is requested, use the listAvailableVideos function to see what's available.
Your goal is to help the user understand their recorded content and provide useful summaries and insights.
Be proactive in providing information from the latest video.
Keep your responses concise and focused on the video content.

IMPORTANT: If there are no videos available, clearly state that but still be helpful. Explain that the user can press F9 to start recording, and press F9 again to stop recording and process the video.
"""

        # Add personalized memory context to the prompt
        memory_prompt = f"""
You have built a memory of the user over time.

USER PROFILE: {memory_context['profile']}

CURRENT FOCUS: {memory_context['current_focus']}

When responding to the user, personalize your response based on this memory.
Refer to their established patterns, preferences, and goals when relevant.
Be conversational and helpful while maintaining appropriate context awareness.
"""
        
        return base_prompt + memory_prompt
    
    def get_tools_config(self):
        """Get the tools configuration for function calling."""
        tools = []
        
        # Add the list videos function
        tools.append(
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="listAvailableVideos",
                        description="List all available recorded videos",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={},
                            required=[],
                        ),
                    ),
                ]
            )
        )
        
        # Add the get video info function
        tools.append(
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="getVideoInfo",
                        description="Get detailed information about a specific video",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "video_id": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="ID of the video to get info for",
                                ),
                            },
                            required=["video_id"],
                        ),
                    ),
                ]
            )
        )
        
        # Add memory access function
        tools.append(
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="getMemoryContext",
                        description="Get the current memory context about the user's patterns and preferences",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={},
                            required=[],
                        ),
                    ),
                ]
            )
        )
        
        return tools
    
    def handle_tool_calls(self, function_calls):
        """Handle tool calls from the model."""
        responses = []
        for call in function_calls:
            name = call.name
            args = call.args
            
            if name == "listAvailableVideos":
                result = self._list_available_videos()
                responses.append({
                    "name": name,
                    "response": result
                })
            
            elif name == "getVideoInfo":
                video_id = args.get("video_id")
                result = self._get_video_info(video_id)
                responses.append({
                    "name": name,
                    "response": result
                })
            
            elif name == "getMemoryContext":
                result = self.memory_manager.get_memory_context()
                responses.append({
                    "name": name,
                    "response": result
                })
        
        return responses
    
    def _list_available_videos(self):
        """List all available videos."""
        videos = []
        for i, video in enumerate(self.conversation_state):
            # Skip status messages
            if isinstance(video, dict) and "status" in video and video["status"] == "skipped":
                continue
                
            # Extract meaningful information
            summary = "No summary available"
            timestamp = "Unknown"
            
            if isinstance(video, dict):
                summary = video.get("summary", "No summary available")
                timestamp = video.get("timestamp", "Unknown")
            
            videos.append({
                "id": i,
                "summary": summary,
                "timestamp": timestamp,
            })
        
        return {
            "videos": videos,
            "count": len(videos)
        }
    
    def _get_video_info(self, video_id):
        """Get detailed information about a specific video."""
        if 0 <= video_id < len(self.conversation_state):
            # Check if it's a skipped video message
            video_data = self.conversation_state[video_id]
            if isinstance(video_data, dict) and "status" in video_data and video_data["status"] == "skipped":
                return {"error": f"This video was already processed. Please request a different video."}
            return self.conversation_state[video_id]
        else:
            return {"error": f"Video with ID {video_id} not found"}
    
    def process_user_input(self, user_input=None):
        """Process user input and generate a response."""
        # Build contents array
        contents = []
        
        # Add message history
        for msg in self.message_history:
            contents.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part.from_text(text=msg["content"])],
                )
            )
        
        # Add user input if any, or use a default prompt
        if user_input:
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_input)],
                )
            )
        else:
            # When no input, ask the agent to provide information about the latest video
            # and incorporate memory context
            memory_context = self.memory_manager.get_memory_context()
            recent_activities = memory_context.get("recent_activities", [])
            
            if self.conversation_state and recent_activities:
                # Get the most recent video ID
                latest_video_id = len(self.conversation_state) - 1
                prompt = f"""Please provide key information about my latest recorded video. 
Include the main points from its analysis, when it was recorded, and insights relevant to my interests and patterns.
Based on your memory of me, personalize the summary to highlight aspects I might find most valuable.
First use getVideoInfo to get the details about video ID {latest_video_id}, then use getMemoryContext to check what you know about me, then provide a helpful personalized summary."""
            else:
                prompt = "Please list any available videos and provide information about what I can do with this system. If there are no videos yet, explain how I can record one."
                
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                )
            )
        
        # Generate content with function calling and system instruction
        generate_content_config = types.GenerateContentConfig(
            tools=self.get_tools_config(),
            system_instruction=[
                types.Part.from_text(text=self._build_system_prompt())
            ],
        )
        
        response = None
        try:
            # Simple approach: just use a basic request-response flow
            response_obj = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=generate_content_config,
            )
            
            # Check if there are function calls in the response
            has_function_calls = False
            for part in response_obj.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call is not None:
                    has_function_calls = True
                    break
            
            if has_function_calls:
                # Extract the function calls from the parts
                function_calls = []
                for part in response_obj.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call is not None:
                        function_calls.append(part.function_call)
                
                # Handle the function calls
                tool_responses = self.handle_tool_calls(function_calls)
                
                # Create a new conversation with the function responses
                new_contents = contents.copy()
                
                # Add the model response with function calls
                new_contents.append(response_obj.candidates[0].content)
                
                # Add function responses
                for tool_response in tool_responses:
                    new_contents.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_function_response(
                                    name=tool_response["name"],
                                    response=tool_response["response"],
                                )
                            ],
                        )
                    )
                
                # Generate a new response with the function results
                final_response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=new_contents,
                    config=generate_content_config,
                )
                
                full_response = final_response.text
            else:
                # No function calls, just use the text response
                full_response = response_obj.text
            
            # Handle edge case where response is empty
            if not full_response.strip():
                full_response = "I don't have any recorded videos to analyze yet. You can press F9 to start recording a video, then press F9 again to stop and have me analyze it."
            
            # Add response to message history
            self.message_history.append({"role": "assistant", "content": full_response})
            
            # Trim message history if it gets too long
            if len(json.dumps(self.message_history)) > 10000:  # Rough token count
                # Keep the first message (system) and the most recent 5 messages
                if len(self.message_history) > 6:
                    self.message_history = [self.message_history[0]] + self.message_history[-5:]
            
            response = full_response
            
        except Exception as e:
            print(f"Error in agent processing: {e}")
            import traceback
            traceback.print_exc()
            response = f"Sorry, I encountered an error: {str(e)}"
        
        return response

if __name__ == "__main__":
    # Example usage
    agent = VideoAgent()
    # Example video data
    video_analysis = {
        "summary": "User recorded a programming session working on a Python project",
        "timestamp": "2023-09-15_14-30-45",
        "transcript": [
            {"time_stamp": "00:00:10", "text": "Let me start by initializing this project"}
        ]
    }
    agent.add_video_to_context(video_analysis)
    response = agent.process_user_input()
    print(response) 