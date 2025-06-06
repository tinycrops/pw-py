import { useState, useEffect } from 'react'
import './App.css'

// Backend API base URL
const API_BASE_URL = 'http://localhost:5001';

function App() {
  const [conversationState, setConversationState] = useState({
    history: [],
    videos: [],
    memory_context: {}
  });
  const [status, setStatus] = useState({
    is_recording: false,
    processed_video_count: 0
  });
  const [lastAgentResponse, setLastAgentResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [isProcessingF9, setIsProcessingF9] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const [isProcessingVideo, setIsProcessingVideo] = useState(false);  // New state to track video processing

  // Query agent on startup to initiate conversation with latest video data
  useEffect(() => {
    const initializeConversation = async () => {
      if (initialized) return;
      
      try {
        setLoading(true);
        // First fetch the status to check if we have videos
        const statusResponse = await fetch(`${API_BASE_URL}/api/status`);
        const statusData = await statusResponse.json();
        
        if (statusData.processed_video_count > 0) {
          // Fetch conversation state to check if there are any assistant messages
          const conversationResponse = await fetch(`${API_BASE_URL}/api/conversation`);
          const conversationData = await conversationResponse.json();
          
          // Check if there are any assistant messages
          const hasAssistantMessages = conversationData.history.some(msg => msg.role === 'assistant');
          
          if (!hasAssistantMessages) {
            // If we have videos but no assistant messages, query the agent
            await queryAgent("Please summarize what videos I have available and what I can do with them.");
          } else {
            // We have videos and assistant messages, just display the last assistant message
            const lastMessage = conversationData.history
              .filter(msg => msg.role === 'assistant')
              .pop();
            
            if (lastMessage) {
              setLastAgentResponse(lastMessage.content);
            }
          }
        } else {
          // No videos, still query agent to get initial welcome message
          await queryAgent("What can I do with this system?");
        }
        
        setInitialized(true);
      } catch (error) {
        console.error('Error initializing conversation:', error);
      } finally {
        setLoading(false);
      }
    };
    
    initializeConversation();
  }, [initialized]);

  // Fetch conversation state periodically
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch status
        const statusResponse = await fetch(`${API_BASE_URL}/api/status`);
        const statusData = await statusResponse.json();
        
        // Only update recording status, don't update UI elements while recording or processing
        if (!status.is_recording && !isProcessingVideo) {
          setStatus(statusData);
        } else {
          // Only update the recording status flag, but keep the video count the same
          // This prevents triggering the "processed_video_count changed" logic during recording
          setStatus(prevStatus => ({
            ...prevStatus,
            is_recording: statusData.is_recording
          }));
        }

        // Only fetch conversation state if not recording or processing
        if (!status.is_recording && !isProcessingVideo) {
          // Fetch conversation
          const conversationResponse = await fetch(`${API_BASE_URL}/api/conversation`);
          const conversationData = await conversationResponse.json();
          setConversationState(conversationData);

          // Update the last agent response only if we're not recording or processing
          if (conversationData.history && conversationData.history.length > 0) {
            const lastMessage = conversationData.history
              .filter(msg => msg.role === 'assistant')
              .pop();
            if (lastMessage) {
              setLastAgentResponse(lastMessage.content);
            }
          }
        }
        
        // Check if recording has finished (only once, when status changes)
        if (status.is_recording && !statusData.is_recording) {
          // Recording just stopped, set processing state
          setIsProcessingVideo(true);
          setLastAgentResponse("Recording stopped. Processing your video, please wait...");
        }
        
        // Only handle video count change when not actively recording
        if (isProcessingVideo && !statusData.is_recording && statusData.processed_video_count > status.processed_video_count) {
          // Processing is done, update video count and exit processing state
          setStatus(statusData);
          setIsProcessingVideo(false);
          
          // Explicitly fetch the latest conversation after processing is complete
          const conversationResponse = await fetch(`${API_BASE_URL}/api/conversation`);
          const conversationData = await conversationResponse.json();
          setConversationState(conversationData);
          
          // Get the newest assistant response
          if (conversationData.history && conversationData.history.length > 0) {
            const lastMessage = conversationData.history
              .filter(msg => msg.role === 'assistant')
              .pop();
            if (lastMessage) {
              setLastAgentResponse(lastMessage.content);
            }
          }
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    // Fetch data immediately and then every 5 seconds
    fetchData();
    const interval = setInterval(fetchData, 5000);

    // Cleanup on component unmount
    return () => clearInterval(interval);
  }, [status.is_recording, status.processed_video_count, isProcessingVideo]);

  // Handle F9 keypress to toggle recording
  useEffect(() => {
    const handleKeyDown = async (event) => {
      if (event.key === 'F9') {
        // Prevent multiple handling of the same F9 press
        if (isProcessingF9 || isProcessingVideo) {
          return;
        }
        
        event.preventDefault();
        setIsProcessingF9(true);
        
        try {
          // If we're not recording, set message before API call
          if (!status.is_recording) {
            setLastAgentResponse("Recording started. Press F9 again when you're done to stop and analyze the recording.");
          }
          
          const response = await fetch(`${API_BASE_URL}/api/toggle_recording`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            }
          });
          const data = await response.json();
          console.log('Recording toggle response:', data);
          
          // Update recording status flag directly
          setStatus(prevStatus => ({
            ...prevStatus,
            is_recording: !prevStatus.is_recording
          }));
          
          // Don't change message here - let the status effect handle it
        } catch (error) {
          console.error('Error toggling recording:', error);
          setLastAgentResponse("Error toggling recording. Please try again.");
        } finally {
          // Add a small delay before allowing another F9 press
          setTimeout(() => {
            setIsProcessingF9(false);
          }, 1000);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isProcessingF9, isProcessingVideo, status.is_recording]);

  // Function to query the agent
  const queryAgent = async (query) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/agent_query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query })
      });
      const data = await response.json();
      setLastAgentResponse(data.response);
      return data.response;
    } catch (error) {
      console.error('Error querying agent:', error);
      setLastAgentResponse("Sorry, I encountered an error communicating with the agent.");
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Function to display memory context summary
  const renderMemorySummary = () => {
    const memory = conversationState.memory_context;
    if (!memory || Object.keys(memory).length === 0) {
      return null;
    }
    
    return (
      <div className="memory-summary">
        <h3>Agent Memory</h3>
        <p><strong>Profile:</strong> {memory.profile || "Building profile..."}</p>
        <p><strong>Current Focus:</strong> {memory.current_focus || "No current focus"}</p>
        {memory.skills && memory.skills.length > 0 && (
          <p><strong>Skills:</strong> {memory.skills.join(", ")}</p>
        )}
      </div>
    );
  };

  // Render the UI
  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Video Journal Assistant</h1>
        <div className="status-indicator">
          {status.is_recording ? 
            <span className="recording">Recording... (Press F9 to stop)</span> : 
            <span className="not-recording">Press F9 to Record</span>
          }
        </div>
      </header>

      <main className="content">
        <section className="agent-response">
          <h2>Assistant</h2>
          <div className="response-box">
            {loading ? (
              <p className="loading">Processing...</p>
            ) : isProcessingVideo ? (
              <p>Recording stopped. Processing your video, please wait...</p>
            ) : (
              <p>{lastAgentResponse || "No response yet. Record a video to start."}</p>
            )}
          </div>
          {renderMemorySummary()}
        </section>

        <section className="video-list">
          <h2>Videos ({status.processed_video_count})</h2>
          <div className="videos-container">
            {conversationState.videos.filter(video => 
              !(video && video.status && video.status === "skipped")
            ).map((video, index) => (
              <div key={index} className="video-card" onClick={() => queryAgent(`Tell me about video ${index}`)}>
                <h3>Video {index + 1}: {new Date(video.timestamp).toLocaleString()}</h3>
                <p>{video.summary}</p>
              </div>
            ))}
            {conversationState.videos.length === 0 && (
              <p>No videos recorded yet. Press F9 to start recording.</p>
            )}
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <p>Press F9 to start/stop recording videos. Click on a video card to get more information.</p>
      </footer>
    </div>
  )
}

export default App
