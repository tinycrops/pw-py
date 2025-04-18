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
        
        base_prompt = """
You have access to information about videos the user has recorded.
Use the getVideoInfo function to retrieve information about specific videos.
If no specific video is requested, use the listAvailableVideos function to see what's available.
Be proactive in providing information from the latest video.
Keep your responses concise and focused on the video content.

You also have advanced memory capabilities to recall and analyze patterns across user interactions:
- Use queryMemoryByTopic to search for information on specific topics across different memory types
- Use analyzeHypothesis to test hypotheses about the user's behaviors and preferences
- Use getFocusedMemoryInsights to get organized insights about user skills, preferences, challenges, etc.
- Use semanticSearchSTM to find semantically related content in short-term memory
- Use compareVideos to identify patterns and relationships between different videos

Be proactive in using these memory tools when they would enhance your response. Don't just rely on what you've been directly told - actively search through memory when it would provide more relevant or personalized information.

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

CRITICAL: Use your memory tools actively to enhance your understanding and provide more valuable insights.
When faced with uncertainty, explore the memory system before stating you don't know.
If appropriate, form and test hypotheses about the user based on observed patterns.
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
        
        # Add query memory by topic function
        tools.append(
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="queryMemoryByTopic",
                        description="Query the memory system for information related to a specific topic or keyword",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "topic": types.Schema(
                                    type=types.Type.STRING,
                                    description="Topic or keyword to search for in memory",
                                ),
                                "memory_type": types.Schema(
                                    type=types.Type.STRING,
                                    description="Type of memory to search: 'short_term', 'working', 'long_term', or 'all'",
                                ),
                            },
                            required=["topic"],
                        ),
                    ),
                ]
            )
        )
        
        # Add hypothesis analysis function
        tools.append(
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="analyzeHypothesis",
                        description="Analyze a hypothesis about the user and check if it can be corroborated by memory evidence",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "hypothesis": types.Schema(
                                    type=types.Type.STRING,
                                    description="The hypothesis about the user to analyze",
                                ),
                            },
                            required=["hypothesis"],
                        ),
                    ),
                ]
            )
        )
        
        # Add get focused memory insights function
        tools.append(
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="getFocusedMemoryInsights",
                        description="Get focused insights from memory about specific user patterns or behaviors",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "aspect": types.Schema(
                                    type=types.Type.STRING,
                                    description="The aspect to focus on: 'skills', 'preferences', 'challenges', 'goals', 'workflows', or 'traits'",
                                ),
                                "detail_level": types.Schema(
                                    type=types.Type.STRING,
                                    description="Level of detail: 'summary' or 'detailed'",
                                ),
                            },
                            required=["aspect"],
                        ),
                    ),
                ]
            )
        )
        
        # Add semantic search in STM function
        tools.append(
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="semanticSearchSTM",
                        description="Perform a semantic search across short-term memory for related concepts",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "query": types.Schema(
                                    type=types.Type.STRING,
                                    description="The query to semantically search for in short-term memory",
                                ),
                                "max_results": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="Maximum number of results to return",
                                ),
                            },
                            required=["query"],
                        ),
                    ),
                ]
            )
        )
        
        # Add compare videos function
        tools.append(
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="compareVideos",
                        description="Compare two videos and identify similarities, differences, and patterns",
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "video_id_1": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="ID of the first video to compare",
                                ),
                                "video_id_2": types.Schema(
                                    type=types.Type.INTEGER,
                                    description="ID of the second video to compare",
                                ),
                            },
                            required=["video_id_1", "video_id_2"],
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
            
            elif name == "queryMemoryByTopic":
                topic = args.get("topic")
                memory_type = args.get("memory_type", "all")
                result = self._query_memory_by_topic(topic, memory_type)
                responses.append({
                    "name": name,
                    "response": result
                })
            
            elif name == "analyzeHypothesis":
                hypothesis = args.get("hypothesis")
                result = self._analyze_hypothesis(hypothesis)
                responses.append({
                    "name": name,
                    "response": result
                })
            
            elif name == "getFocusedMemoryInsights":
                aspect = args.get("aspect")
                detail_level = args.get("detail_level", "summary")
                result = self._get_focused_memory_insights(aspect, detail_level)
                responses.append({
                    "name": name,
                    "response": result
                })
            
            elif name == "semanticSearchSTM":
                query = args.get("query")
                max_results = args.get("max_results", 3)
                result = self._semantic_search_stm(query, max_results)
                responses.append({
                    "name": name,
                    "response": result
                })
            
            elif name == "compareVideos":
                video_id_1 = args.get("video_id_1")
                video_id_2 = args.get("video_id_2")
                result = self._compare_videos(video_id_1, video_id_2)
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

    def _compare_videos(self, video_id_1, video_id_2):
        """Compare two videos and identify similarities, differences, and patterns."""
        # Get video data for both videos
        video1 = self._get_video_info(video_id_1)
        video2 = self._get_video_info(video_id_2)
        
        # Check if either video retrieval resulted in an error
        if "error" in video1:
            return {"error": f"Could not compare videos: {video1['error']}"}
        if "error" in video2:
            return {"error": f"Could not compare videos: {video2['error']}"}
        
        # Extract summaries, topics, and actions for comparison
        summary1 = video1.get("summary", "No summary available")
        summary2 = video2.get("summary", "No summary available")
        
        topics1 = set(video1.get("topics", []))
        topics2 = set(video2.get("topics", []))
        
        common_topics = topics1.intersection(topics2)
        unique_topics1 = topics1.difference(topics2)
        unique_topics2 = topics2.difference(topics1)
        
        actions1 = video1.get("actions", "")
        actions2 = video2.get("actions", "")
        
        # Build and return comparison result
        result = {
            "video1": {
                "id": video_id_1,
                "summary": summary1,
                "timestamp": video1.get("timestamp", "Unknown")
            },
            "video2": {
                "id": video_id_2,
                "summary": summary2,
                "timestamp": video2.get("timestamp", "Unknown")
            },
            "comparison": {
                "common_topics": list(common_topics),
                "unique_topics_video1": list(unique_topics1),
                "unique_topics_video2": list(unique_topics2),
                "time_difference": "Unknown"  # Could calculate if timestamps are standardized
            },
            "analysis": {
                "similarity": "High" if len(common_topics) > max(1, min(len(topics1), len(topics2)) // 2) else "Low",
                "progression": self._analyze_progression(video1, video2),
                "pattern_observation": "The videos appear to be part of a sequence" if self._check_sequence(video1, video2) else "The videos appear to be independent"
            }
        }
        
        return result
    
    def _analyze_progression(self, video1, video2):
        """Analyze if there's a progression or continuation between videos."""
        # Simple heuristic: check if summary of video2 references continuation
        continuation_words = ["continue", "next", "further", "again", "progress", "more"]
        summary2 = video2.get("summary", "").lower()
        
        if any(word in summary2 for word in continuation_words):
            return "Video 2 appears to be a continuation of Video 1"
        
        # Compare timestamps if available
        try:
            time1 = video1.get("timestamp", "")
            time2 = video2.get("timestamp", "")
            
            if time1 and time2 and time1 < time2:
                return "Video 2 was recorded after Video 1"
        except:
            pass
            
        return "No clear progression detected"
    
    def _check_sequence(self, video1, video2):
        """Check if two videos appear to be in a logical sequence."""
        # Placeholder for more complex logic
        # In a real implementation, this could look at content to determine sequence
        return False
    
    def _query_memory_by_topic(self, topic, memory_type="all"):
        """Query memory for information related to a specific topic."""
        # Convert topic to lowercase for case-insensitive matching
        search_term = topic.lower()
        results = {
            "topic": topic,
            "memory_type": memory_type,
            "results": []
        }
        
        # Search short-term memory if requested
        if memory_type in ["short_term", "all"]:
            stm_results = []
            for entry in self.memory_manager.short_term_memory:
                if self._matches_search(entry, search_term):
                    stm_results.append(self._sanitize_memory_entry(entry))
            
            if stm_results:
                results["results"].append({
                    "memory_component": "short_term_memory",
                    "entries": stm_results
                })
        
        # Search working memory if requested
        if memory_type in ["working", "all"]:
            wm_results = []
            
            # Search in untested hypotheses
            for hypothesis in self.memory_manager.working_memory.get("untested_hypotheses", []):
                if search_term in hypothesis.get("insight", "").lower():
                    wm_results.append({
                        "type": "untested_hypothesis",
                        "data": hypothesis
                    })
            
            # Search in corroborated hypotheses
            for hypothesis in self.memory_manager.working_memory.get("corroborated_hypotheses", []):
                if search_term in hypothesis.get("insight", "").lower():
                    wm_results.append({
                        "type": "corroborated_hypothesis",
                        "data": hypothesis
                    })
            
            # Search in established facts
            for fact in self.memory_manager.working_memory.get("established_facts", []):
                if search_term in fact.get("insight", "").lower():
                    wm_results.append({
                        "type": "established_fact",
                        "data": fact
                    })
            
            if wm_results:
                results["results"].append({
                    "memory_component": "working_memory",
                    "entries": wm_results
                })
        
        # Search long-term memory if requested
        if memory_type in ["long_term", "all"]:
            ltm_results = []
            
            # Search in skills
            for skill in self.memory_manager.long_term_memory.get("skills_and_knowledge", {}).get("confirmed_skills", []):
                if search_term in skill.lower():
                    ltm_results.append({
                        "category": "skill",
                        "data": skill
                    })
            
            # Search in preferences
            for pref in self.memory_manager.long_term_memory.get("preferences_and_habits", {}).get("workflow_habits", []):
                if search_term in pref.lower():
                    ltm_results.append({
                        "category": "preference",
                        "data": pref
                    })
            
            # Search in challenges
            for challenge in self.memory_manager.long_term_memory.get("challenges", {}).get("difficulties", []):
                if search_term in challenge.lower():
                    ltm_results.append({
                        "category": "challenge",
                        "data": challenge
                    })
            
            # Search in goals
            for goal in self.memory_manager.long_term_memory.get("goals_and_motivations", {}).get("inferred_goals", []):
                if search_term in goal.lower():
                    ltm_results.append({
                        "category": "goal",
                        "data": goal
                    })
            
            if ltm_results:
                results["results"].append({
                    "memory_component": "long_term_memory",
                    "entries": ltm_results
                })
        
        # Add result metadata
        results["total_matches"] = sum(len(component["entries"]) for component in results["results"])
        
        return results
    
    def _matches_search(self, entry, search_term):
        """Check if a memory entry matches the search term."""
        if entry.get("type") == "video_analysis":
            # Search in summary
            if search_term in entry.get("summary", "").lower():
                return True
            
            # Search in topics
            for topic in entry.get("topics", []):
                if search_term in topic.lower():
                    return True
            
            # Search in tags
            for tag in entry.get("tags", []):
                if search_term in tag.lower():
                    return True
            
            # Search in actions
            if search_term in entry.get("actions", "").lower():
                return True
            
            # Search in transcript excerpts
            if "transcript_excerpt" in entry:
                excerpt = entry["transcript_excerpt"]
                if isinstance(excerpt, dict):
                    # For structured excerpts with start/end
                    for part in excerpt.get("start", []):
                        if isinstance(part, dict) and search_term in part.get("text", "").lower():
                            return True
                    for part in excerpt.get("end", []):
                        if isinstance(part, dict) and search_term in part.get("text", "").lower():
                            return True
                elif isinstance(excerpt, str):
                    # For string excerpts
                    if search_term in excerpt.lower():
                        return True
        
        return False
    
    def _sanitize_memory_entry(self, entry):
        """Sanitize a memory entry for API response (remove sensitive or redundant data)."""
        if entry.get("type") == "video_analysis":
            return {
                "type": entry.get("type"),
                "timestamp": entry.get("timestamp"),
                "summary": entry.get("summary"),
                "topics": entry.get("topics", []),
                "tags": entry.get("tags", [])
            }
        return entry
    
    def _analyze_hypothesis(self, hypothesis):
        """Analyze a hypothesis about the user and check if it can be corroborated."""
        hypothesis_text = hypothesis.lower()
        evidence = []
        counter_evidence = []
        
        # Check short-term memory for evidence
        for entry in self.memory_manager.short_term_memory:
            if entry.get("type") == "video_analysis":
                summary = entry.get("summary", "").lower()
                actions = entry.get("actions", "").lower()
                
                # Simple approach: if the hypothesis appears in the text, consider it evidence
                if any(term in summary or term in actions for term in hypothesis_text.split()):
                    evidence.append({
                        "source": "short_term_memory",
                        "entry_type": "video_analysis",
                        "timestamp": entry.get("timestamp"),
                        "content": entry.get("summary")
                    })
        
        # Check working memory
        # First look at established facts
        for fact in self.memory_manager.working_memory.get("established_facts", []):
            fact_text = fact.get("insight", "").lower()
            # If the fact supports the hypothesis
            if any(term in fact_text for term in hypothesis_text.split()):
                evidence.append({
                    "source": "working_memory",
                    "entry_type": "established_fact",
                    "content": fact.get("insight"),
                    "original_evidence": fact.get("evidence")
                })
            # If the fact contradicts the hypothesis (simple negation check)
            elif "not " + hypothesis_text in fact_text or hypothesis_text.replace("not ", "") in fact_text:
                counter_evidence.append({
                    "source": "working_memory",
                    "entry_type": "established_fact",
                    "content": fact.get("insight"),
                    "original_evidence": fact.get("evidence")
                })
        
        # Then look at corroborated hypotheses
        for hyp in self.memory_manager.working_memory.get("corroborated_hypotheses", []):
            hyp_text = hyp.get("insight", "").lower()
            # If the hypothesis aligns
            if any(term in hyp_text for term in hypothesis_text.split()):
                evidence.append({
                    "source": "working_memory",
                    "entry_type": "corroborated_hypothesis",
                    "content": hyp.get("insight"),
                    "original_evidence": hyp.get("evidence")
                })
        
        # Check against long-term memory patterns
        ltm_evidence = []
        
        # Check if hypothesis relates to skills
        if any(term in hypothesis_text for term in ["skill", "know", "able", "can"]):
            for skill in self.memory_manager.long_term_memory.get("skills_and_knowledge", {}).get("confirmed_skills", []):
                if any(term in skill.lower() for term in hypothesis_text.split()):
                    ltm_evidence.append({
                        "category": "skill",
                        "content": skill
                    })
        
        # Check if hypothesis relates to preferences
        if any(term in hypothesis_text for term in ["prefer", "like", "enjoy", "favorite"]):
            for pref in self.memory_manager.long_term_memory.get("preferences_and_habits", {}).get("workflow_habits", []):
                if any(term in pref.lower() for term in hypothesis_text.split()):
                    ltm_evidence.append({
                        "category": "preference",
                        "content": pref
                    })
        
        # Determine the status of the hypothesis
        status = "unverified"
        confidence = 0.0
        
        # Calculate confidence based on evidence
        if evidence:
            # More evidence means higher confidence
            confidence = min(0.9, 0.3 + (len(evidence) * 0.15))
            
            if counter_evidence:
                # Counter evidence reduces confidence
                confidence = max(0.1, confidence - (len(counter_evidence) * 0.2))
                status = "conflicting_evidence"
            else:
                if len(evidence) >= 3:
                    status = "strongly_supported"
                else:
                    status = "supported"
        elif counter_evidence:
            status = "contradicted"
            confidence = 0.1
        
        # If we have LTM evidence, add it and boost confidence
        if ltm_evidence:
            evidence.extend([{"source": "long_term_memory", **item} for item in ltm_evidence])
            confidence = min(0.95, confidence + 0.1)
            
            if status == "unverified":
                status = "supported_by_ltm"
        
        # Prepare the result
        result = {
            "hypothesis": hypothesis,
            "status": status,
            "confidence": round(confidence, 2),
            "evidence": evidence,
            "counter_evidence": counter_evidence,
            "evidence_count": len(evidence),
            "counter_evidence_count": len(counter_evidence)
        }
        
        return result
    
    def _get_focused_memory_insights(self, aspect, detail_level="summary"):
        """Get focused insights from memory about specific user aspects."""
        aspect = aspect.lower()
        insights = {
            "aspect": aspect,
            "detail_level": detail_level
        }
        
        if aspect == "skills":
            # Get skills info from LTM
            confirmed = self.memory_manager.long_term_memory.get("skills_and_knowledge", {}).get("confirmed_skills", [])
            inferred = self.memory_manager.long_term_memory.get("skills_and_knowledge", {}).get("inferred_skills", [])
            
            insights["data"] = {
                "confirmed_skills": confirmed,
                "inferred_skills": inferred
            }
            
            # Add skill-related hypotheses from working memory
            if detail_level == "detailed":
                skill_hypotheses = []
                for hypo_type in ["established_facts", "corroborated_hypotheses"]:
                    for hypo in self.memory_manager.working_memory.get(hypo_type, []):
                        if any(skill_word in hypo.get("insight", "").lower() 
                               for skill_word in ["skill", "know", "can", "able", "proficient"]):
                            skill_hypotheses.append(hypo)
                
                insights["related_hypotheses"] = skill_hypotheses
        
        elif aspect == "preferences":
            # Get preference info from LTM
            ui_prefs = self.memory_manager.long_term_memory.get("preferences_and_habits", {}).get("ui_preferences", [])
            workflow = self.memory_manager.long_term_memory.get("preferences_and_habits", {}).get("workflow_habits", [])
            tools = self.memory_manager.long_term_memory.get("preferences_and_habits", {}).get("tool_preferences", [])
            
            insights["data"] = {
                "ui_preferences": ui_prefs,
                "workflow_habits": workflow,
                "tool_preferences": tools
            }
            
            # Add preference-related working memory
            if detail_level == "detailed":
                pref_hypotheses = []
                for hypo_type in ["established_facts", "corroborated_hypotheses"]:
                    for hypo in self.memory_manager.working_memory.get(hypo_type, []):
                        if any(pref_word in hypo.get("insight", "").lower() 
                               for pref_word in ["prefer", "like", "enjoy", "favorite"]):
                            pref_hypotheses.append(hypo)
                
                insights["related_hypotheses"] = pref_hypotheses
        
        elif aspect == "challenges":
            # Get challenges from LTM
            frustrations = self.memory_manager.long_term_memory.get("challenges", {}).get("recurring_frustrations", [])
            difficulties = self.memory_manager.long_term_memory.get("challenges", {}).get("difficulties", [])
            blockers = self.memory_manager.long_term_memory.get("challenges", {}).get("blockers", [])
            
            insights["data"] = {
                "recurring_frustrations": frustrations,
                "difficulties": difficulties,
                "blockers": blockers
            }
            
            # Add challenge-related STM entries
            if detail_level == "detailed":
                challenge_entries = []
                for entry in self.memory_manager.short_term_memory:
                    if entry.get("type") == "video_analysis":
                        summary = entry.get("summary", "").lower()
                        if any(challenge_word in summary 
                               for challenge_word in ["error", "problem", "issue", "difficult", "challenge", "struggle"]):
                            challenge_entries.append(self._sanitize_memory_entry(entry))
                
                insights["recent_challenge_entries"] = challenge_entries
        
        elif aspect == "goals":
            # Get goals from LTM
            stated = self.memory_manager.long_term_memory.get("goals_and_motivations", {}).get("stated_goals", [])
            inferred = self.memory_manager.long_term_memory.get("goals_and_motivations", {}).get("inferred_goals", [])
            motivations = self.memory_manager.long_term_memory.get("goals_and_motivations", {}).get("motivations", [])
            
            insights["data"] = {
                "stated_goals": stated,
                "inferred_goals": inferred,
                "motivations": motivations
            }
        
        elif aspect == "workflows":
            # Get workflow info from LTM
            tasks = self.memory_manager.long_term_memory.get("workflows", {}).get("common_tasks", [])
            approaches = self.memory_manager.long_term_memory.get("workflows", {}).get("approaches", [])
            patterns = self.memory_manager.long_term_memory.get("workflows", {}).get("frequency_patterns", [])
            
            insights["data"] = {
                "common_tasks": tasks,
                "approaches": approaches,
                "frequency_patterns": patterns
            }
            
            # Add workflow-related hypotheses
            if detail_level == "detailed":
                workflow_hypotheses = []
                for hypo_type in ["established_facts", "corroborated_hypotheses"]:
                    for hypo in self.memory_manager.working_memory.get(hypo_type, []):
                        if "workflow" in hypo.get("insight", "").lower():
                            workflow_hypotheses.append(hypo)
                
                insights["related_hypotheses"] = workflow_hypotheses
        
        elif aspect == "traits":
            # Get traits from LTM
            comm_style = self.memory_manager.long_term_memory.get("traits_and_attitudes", {}).get("communication_style", [])
            decision = self.memory_manager.long_term_memory.get("traits_and_attitudes", {}).get("decision_making", [])
            learning = self.memory_manager.long_term_memory.get("traits_and_attitudes", {}).get("learning_approach", [])
            
            insights["data"] = {
                "communication_style": comm_style,
                "decision_making": decision,
                "learning_approach": learning
            }
        
        else:
            # Unrecognized aspect
            return {
                "error": f"Unrecognized aspect: {aspect}",
                "valid_aspects": ["skills", "preferences", "challenges", "goals", "workflows", "traits"]
            }
        
        # Add a summary
        insights["summary"] = self._generate_insight_summary(aspect, insights["data"])
        
        return insights
    
    def _generate_insight_summary(self, aspect, data):
        """Generate a summary of the insights for a specific aspect."""
        if aspect == "skills":
            confirmed_count = len(data.get("confirmed_skills", []))
            inferred_count = len(data.get("inferred_skills", []))
            
            if confirmed_count == 0 and inferred_count == 0:
                return "No skills identified yet."
            
            top_skills = data.get("confirmed_skills", [])[:3]
            skill_str = ", ".join(top_skills) if top_skills else "none confirmed yet"
            
            return f"User has {confirmed_count} confirmed skills (top: {skill_str}) and {inferred_count} inferred skills."
        
        elif aspect == "preferences":
            workflow_count = len(data.get("workflow_habits", []))
            tool_count = len(data.get("tool_preferences", []))
            
            if workflow_count == 0 and tool_count == 0:
                return "No preferences identified yet."
            
            return f"User has {workflow_count} workflow preferences and {tool_count} tool preferences."
        
        elif aspect == "challenges":
            difficulty_count = len(data.get("difficulties", []))
            blocker_count = len(data.get("blockers", []))
            
            if difficulty_count == 0 and blocker_count == 0:
                return "No challenges identified yet."
            
            return f"User has experienced {difficulty_count} difficulties and {blocker_count} blockers."
        
        elif aspect == "goals":
            stated_count = len(data.get("stated_goals", []))
            inferred_count = len(data.get("inferred_goals", []))
            
            if stated_count == 0 and inferred_count == 0:
                return "No goals identified yet."
            
            return f"User has {stated_count} stated goals and {inferred_count} inferred goals."
        
        elif aspect == "workflows":
            task_count = len(data.get("common_tasks", []))
            approach_count = len(data.get("approaches", []))
            
            if task_count == 0 and approach_count == 0:
                return "No workflow patterns identified yet."
            
            return f"User has {task_count} common tasks and {approach_count} approach patterns."
        
        elif aspect == "traits":
            comm_count = len(data.get("communication_style", []))
            decision_count = len(data.get("decision_making", []))
            learning_count = len(data.get("learning_approach", []))
            
            if comm_count == 0 and decision_count == 0 and learning_count == 0:
                return "No traits identified yet."
            
            return f"User has {comm_count} communication style traits, {decision_count} decision-making traits, and {learning_count} learning approach traits."
        
        return "No summary available."
    
    def _semantic_search_stm(self, query, max_results=3):
        """
        Perform a semantic search across short-term memory.
        This is a simplified implementation that simulates semantic search with keyword matching.
        In a real implementation, this would use embeddings and vector similarity.
        """
        # Split query into terms for matching
        query_terms = query.lower().split()
        
        # Score each STM entry
        scored_entries = []
        for entry in self.memory_manager.short_term_memory:
            if entry.get("type") == "video_analysis":
                # Calculate a simple relevance score
                score = 0
                
                # Check summary
                summary = entry.get("summary", "").lower()
                for term in query_terms:
                    if term in summary:
                        score += 2  # Summary matches are more important
                
                # Check topics
                for topic in entry.get("topics", []):
                    for term in query_terms:
                        if term in topic.lower():
                            score += 3  # Topic matches are very relevant
                
                # Check actions
                actions = entry.get("actions", "").lower()
                for term in query_terms:
                    if term in actions:
                        score += 1
                
                # If there's any match, add to results
                if score > 0:
                    scored_entries.append({
                        "entry": self._sanitize_memory_entry(entry),
                        "score": score
                    })
        
        # Sort by score descending
        scored_entries.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top results
        top_results = scored_entries[:max_results]
        
        return {
            "query": query,
            "total_matches": len(scored_entries),
            "results": [
                {
                    "score": item["score"],
                    "entry": item["entry"]
                }
                for item in top_results
            ]
        }

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