import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Token limits for different memory components
STM_TOKEN_LIMIT = 8000
WM_TOKEN_LIMIT = 4000
LTM_TOKEN_LIMIT = 12000

# Memory file paths
MEMORY_DIR = "agent_memory"
STM_FILE = os.path.join(MEMORY_DIR, "short_term_memory.json")
WM_FILE = os.path.join(MEMORY_DIR, "working_memory.json")
LTM_FILE = os.path.join(MEMORY_DIR, "long_term_memory.json")

class MemoryManager:
    """
    Manages a multi-tiered memory system for the agent with:
    - Short-Term Memory (STM): Recent observations and interactions
    - Working Memory (WM): Current session context and hypotheses
    - Long-Term Memory (LTM): Persistent user profile and patterns
    """
    
    def __init__(self):
        """Initialize the memory manager and load existing memory if available."""
        # Create memory directory if it doesn't exist
        os.makedirs(MEMORY_DIR, exist_ok=True)
        
        # Initialize memory components
        self.short_term_memory = self._load_memory(STM_FILE, [])
        self.working_memory = self._load_memory(WM_FILE, {
            "untested_hypotheses": [],
            "corroborated_hypotheses": [],
            "established_facts": []
        })
        self.long_term_memory = self._load_memory(LTM_FILE, {
            "profile_summary": "New user profile - limited information available",
            "skills_and_knowledge": {
                "confirmed_skills": [],
                "inferred_skills": [],
                "knowledge_gaps": []
            },
            "preferences_and_habits": {
                "ui_preferences": [],
                "workflow_habits": [],
                "tool_preferences": []
            },
            "workflows": {
                "common_tasks": [],
                "approaches": [],
                "frequency_patterns": []
            },
            "challenges": {
                "recurring_frustrations": [],
                "difficulties": [],
                "blockers": []
            },
            "goals_and_motivations": {
                "stated_goals": [],
                "inferred_goals": [],
                "motivations": []
            },
            "traits_and_attitudes": {
                "communication_style": [],
                "decision_making": [],
                "learning_approach": []
            }
        })
        
    def _load_memory(self, filepath, default_value):
        """Load memory from file if it exists, otherwise return default."""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading memory from {filepath}: {e}")
                return default_value
        return default_value
    
    def _save_memory(self, filepath, memory_data):
        """Save memory data to file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(memory_data, f, indent=2)
        except Exception as e:
            print(f"Error saving memory to {filepath}: {e}")
    
    def add_to_stm(self, entry):
        """Add a new entry to short-term memory."""
        # Add timestamp if not present
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat()
            
        # Add the entry to STM
        self.short_term_memory.append(entry)
        
        # Limit STM size by removing oldest entries if needed
        while self._estimate_tokens(self.short_term_memory) > STM_TOKEN_LIMIT:
            if len(self.short_term_memory) > 0:
                self.short_term_memory.pop(0)
            else:
                break
                
        # Save the updated STM
        self._save_memory(STM_FILE, self.short_term_memory)
        
    def add_video_analysis_to_memory(self, video_analysis):
        """Process video analysis and add it to the memory system."""
        # Extract relevant information from the video analysis
        if isinstance(video_analysis, dict):
            # For status messages or error messages, handle differently
            if "status" in video_analysis and video_analysis["status"] == "skipped":
                # This is a skipped video notification, not actual analysis
                print("Skipping already processed video in memory update")
                return
                
            # Extract core information for memory
            memory_entry = {
                "type": "video_analysis",
                "timestamp": video_analysis.get("timestamp", datetime.now().isoformat()),
                "summary": video_analysis.get("summary", "No summary available"),
                "topics": video_analysis.get("topics", []),
                "tags": video_analysis.get("tags", []),
                "actions": video_analysis.get("actions", ""),
                "screenContent": video_analysis.get("screenContent", "")
            }
            
            # Add transcript summary if available
            if "transcript" in video_analysis and video_analysis["transcript"]:
                # For transcript arrays with time_stamp format
                if isinstance(video_analysis["transcript"], list):
                    # Just store the first few and last few lines to save space
                    if len(video_analysis["transcript"]) > 10:
                        memory_entry["transcript_excerpt"] = {
                            "start": video_analysis["transcript"][:3],
                            "end": video_analysis["transcript"][-3:]
                        }
                    else:
                        memory_entry["transcript_excerpt"] = video_analysis["transcript"]
                else:
                    # For simple string transcripts
                    memory_entry["transcript_excerpt"] = video_analysis["transcript"][:500] + "..."
            
            # Add to short-term memory
            self.add_to_stm(memory_entry)
            
            # Update working memory and long-term memory
            self.update_memories()
            
    def update_memories(self):
        """Update working memory and long-term memory based on STM."""
        # Update long-term memory first
        self.update_ltm()
        
        # Then update working memory
        self.update_wm()
    
    def update_wm(self):
        """
        Update working memory with the most relevant information from STM and LTM.
        This implements a cognitive hierarchy with hypotheses and facts.
        """
        # For simplicity in this initial implementation, we'll extract recent insights
        # and important patterns from STM and LTM
        
        # Get recent STM entries
        recent_entries = self.short_term_memory[-5:] if len(self.short_term_memory) > 5 else self.short_term_memory
        
        # Extract potential hypotheses from recent activities
        new_hypotheses = []
        for entry in recent_entries:
            if entry.get("type") == "video_analysis":
                # Extract topics as potential focus areas
                for topic in entry.get("topics", []):
                    hypothesis = {
                        "insight": f"User is currently focused on {topic}",
                        "evidence": f"[Topic in recent video: {entry.get('summary')}]",
                        "relevance": "Current focus area"
                    }
                    new_hypotheses.append(hypothesis)
                
                # Extract actions as potential workflow patterns
                if "actions" in entry and entry["actions"]:
                    hypothesis = {
                        "insight": f"User workflow involves: {entry['actions']}",
                        "evidence": f"[Actions in recent video]",
                        "relevance": "Current workflow pattern"
                    }
                    new_hypotheses.append(hypothesis)
        
        # Merge with existing hypotheses, promoting if there's corroboration
        untested = self.working_memory["untested_hypotheses"].copy()
        corroborated = self.working_memory["corroborated_hypotheses"].copy()
        established = self.working_memory["established_facts"].copy()
        
        # Add new hypotheses to untested list if they don't already exist
        for new_h in new_hypotheses:
            if not any(h["insight"] == new_h["insight"] for h in untested + corroborated + established):
                untested.append(new_h)
        
        # Promote hypotheses based on evidence
        for i, hypothesis in enumerate(untested):
            # Check if this hypothesis appears in multiple STM entries
            evidence_count = 0
            for entry in self.short_term_memory:
                # Simple text matching - could be more sophisticated
                if entry.get("type") == "video_analysis":
                    content = entry.get("summary", "") + " " + entry.get("actions", "")
                    if hypothesis["insight"].lower() in content.lower():
                        evidence_count += 1
            
            # If we have multiple pieces of evidence, promote to corroborated
            if evidence_count >= 2:
                # Update evidence to reflect multiple observations
                hypothesis["evidence"] = f"{hypothesis['evidence']} + {evidence_count-1} more observations"
                corroborated.append(hypothesis)
                untested[i] = None  # Mark for removal
        
        # Remove promoted hypotheses from untested
        untested = [h for h in untested if h is not None]
        
        # Similarly check for promotion from corroborated to established
        for i, hypothesis in enumerate(corroborated):
            evidence_count = 0
            for entry in self.short_term_memory:
                if entry.get("type") == "video_analysis":
                    content = entry.get("summary", "") + " " + entry.get("actions", "")
                    if hypothesis["insight"].lower() in content.lower():
                        evidence_count += 1
            
            # If consistently supported across 3+ observations, promote to fact
            if evidence_count >= 3:
                hypothesis["evidence"] = f"Consistently observed across {evidence_count} interactions"
                established.append(hypothesis)
                corroborated[i] = None
        
        # Remove promoted hypotheses from corroborated
        corroborated = [h for h in corroborated if h is not None]
        
        # Update working memory with new hypotheses and facts
        self.working_memory = {
            "untested_hypotheses": untested,
            "corroborated_hypotheses": corroborated,
            "established_facts": established
        }
        
        # Save the updated working memory
        self._save_memory(WM_FILE, self.working_memory)
    
    def update_ltm(self):
        """
        Update long-term memory by integrating patterns from STM.
        This builds a persistent user profile over time.
        """
        # For initial implementation, we'll extract key patterns from STM
        # and integrate them into the LTM structure
        
        # Extract skills, preferences, and challenges from STM
        skills = set()
        preferences = set()
        challenges = set()
        goals = set()
        
        # Analyze STM entries for patterns
        for entry in self.short_term_memory:
            if entry.get("type") == "video_analysis":
                # Extract skills from topics and tags
                for topic in entry.get("topics", []):
                    if any(tech in topic.lower() for tech in ["programming", "coding", "development", "python", "javascript", "ai"]):
                        skills.add(topic)
                
                # Extract preferences from actions and screen content
                actions = entry.get("actions", "")
                if "preferred" in actions.lower() or "likes" in actions.lower():
                    preferences.add(actions)
                
                # Extract challenges from summary
                summary = entry.get("summary", "")
                if any(word in summary.lower() for word in ["difficult", "challenging", "struggle", "error", "problem", "issue"]):
                    challenges.add(summary)
                
                # Extract potential goals from summary and actions
                if any(word in summary.lower() for word in ["goal", "aim", "objective", "trying to", "want to"]):
                    goals.add(summary)
        
        # Update LTM with new information
        # Add confirmed skills
        for skill in skills:
            if skill not in self.long_term_memory["skills_and_knowledge"]["confirmed_skills"]:
                self.long_term_memory["skills_and_knowledge"]["confirmed_skills"].append(skill)
        
        # Add preferences
        for pref in preferences:
            if pref not in self.long_term_memory["preferences_and_habits"]["workflow_habits"]:
                self.long_term_memory["preferences_and_habits"]["workflow_habits"].append(pref)
        
        # Add challenges
        for challenge in challenges:
            if challenge not in self.long_term_memory["challenges"]["difficulties"]:
                self.long_term_memory["challenges"]["difficulties"].append(challenge)
        
        # Add goals
        for goal in goals:
            if goal not in self.long_term_memory["goals_and_motivations"]["inferred_goals"]:
                self.long_term_memory["goals_and_motivations"]["inferred_goals"].append(goal)
        
        # Update profile summary
        if skills or preferences or challenges or goals:
            skill_str = ", ".join(list(skills)[:3]) if skills else "unknown skills"
            pref_str = ", ".join(list(preferences)[:2]) if preferences else "unknown preferences"
            summary = f"User profile with focus on {skill_str}, with {pref_str}"
            self.long_term_memory["profile_summary"] = summary
        
        # Save updated LTM
        self._save_memory(LTM_FILE, self.long_term_memory)
    
    def get_memory_context(self):
        """
        Get the current state of the memory system for use in agent responses.
        Returns a consolidated view of relevant memory components.
        """
        # Combine the most relevant aspects of STM, WM, and LTM
        memory_context = {
            "profile": self.long_term_memory["profile_summary"],
            "current_focus": self._extract_current_focus(),
            "established_facts": self.working_memory["established_facts"],
            "recent_activities": self._get_recent_activities(3),  # Last 3 activities
            "skills": self.long_term_memory["skills_and_knowledge"]["confirmed_skills"],
            "preferences": self.long_term_memory["preferences_and_habits"]["workflow_habits"],
            "challenges": self.long_term_memory["challenges"]["difficulties"],
            "goals": self.long_term_memory["goals_and_motivations"]["inferred_goals"] + 
                    self.long_term_memory["goals_and_motivations"]["stated_goals"]
        }
        return memory_context
    
    def _extract_current_focus(self):
        """Extract the user's current focus from working memory."""
        # Check established facts first
        for fact in self.working_memory["established_facts"]:
            if "currently focused on" in fact["insight"]:
                return fact["insight"]
        
        # Then check corroborated hypotheses
        for hypo in self.working_memory["corroborated_hypotheses"]:
            if "currently focused on" in hypo["insight"]:
                return hypo["insight"]
        
        # Then latest activity from STM
        if self.short_term_memory:
            latest = self.short_term_memory[-1]
            if latest.get("type") == "video_analysis":
                return f"Recently recorded video about {latest.get('summary', 'unknown topic')}"
        
        return "No clear current focus"
    
    def _get_recent_activities(self, count=3):
        """Get the most recent activities from STM."""
        activities = []
        for entry in reversed(self.short_term_memory[-count:]):
            if entry.get("type") == "video_analysis":
                activities.append({
                    "timestamp": entry.get("timestamp"),
                    "summary": entry.get("summary"),
                    "topics": entry.get("topics", [])
                })
        return activities
    
    def _estimate_tokens(self, data):
        """Roughly estimate token count of data structure."""
        # Very rough estimate: 1 token ≈ 4 characters in English
        json_str = json.dumps(data)
        return len(json_str) / 4

# Singleton instance
_memory_manager = None

def get_memory_manager():
    """Get or create the singleton MemoryManager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager 