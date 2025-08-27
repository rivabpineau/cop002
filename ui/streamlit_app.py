# Streamlit chat UI application
# RIVA ChatGPT - ChatGPT-like interface using Streamlit

import streamlit as st
import os
import json
import time
import httpx
from typing import List, Dict, Any, Optional
from sseclient import SSEClient

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# Page configuration
st.set_page_config(
    page_title="RIVA ChatGPT",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        font-size: 2.5rem;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .assistant-message {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
    .stButton > button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        background-color: #1565c0;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "temperature" not in st.session_state:
        st.session_state.temperature = 0.2
    
    if "max_tokens" not in st.session_state:
        st.session_state.max_tokens = 500
    
    if "backend_url" not in st.session_state:
        st.session_state.backend_url = BACKEND_URL

def display_message(role: str, content: str):
    """Display a chat message with proper styling"""
    with st.chat_message(role):
        st.markdown(content)

def clear_chat():
    """Clear the chat history"""
    st.session_state.messages = []
    st.rerun()

def stream_chat_response(messages: List[Dict[str, str]], temperature: float, max_tokens: int, backend_url: str) -> Optional[str]:
    """
    Stream chat response from the backend API
    
    Args:
        messages: List of message dictionaries with role and content
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        backend_url: Backend API URL
        
    Returns:
        str: Complete response text, or None if failed
    """
    try:
        # Prepare the request payload
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        # Make streaming request to backend
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        # Create placeholder for streaming text
        response_placeholder = st.empty()
        accumulated_text = ""
        
        # Initialize stop button state
        if "stop_generation" not in st.session_state:
            st.session_state.stop_generation = False
        
        # Add stop button
        stop_button_placeholder = st.empty()
        
        with httpx.Client(timeout=60.0) as client:
            with client.stream(
                "POST",
                f"{backend_url}/chat",
                json=payload,
                headers=headers
            ) as response:
                
                # Check if request was successful
                if response.status_code != 200:
                    error_msg = f"Backend error: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('detail', 'Unknown error')}"
                    except:
                        pass
                    st.error(error_msg)
                    return None
                
                # Process SSE stream
                for line in response.iter_lines():
                    # Check for stop generation
                    if st.session_state.stop_generation:
                        st.session_state.stop_generation = False
                        st.info("⏹️ Generation stopped by user")
                        break
                    
                    # Add stop button during streaming
                    if stop_button_placeholder:
                        with stop_button_placeholder.container():
                            if st.button("⏹️ Stop Generation", key=f"stop_{time.time()}"):
                                st.session_state.stop_generation = True
                                break
                    
                    if line.startswith("data: "):
                        try:
                            # Parse SSE data
                            event_data = json.loads(line[6:])  # Remove "data: " prefix
                            
                            if event_data.get("type") == "token":
                                # Add token to accumulated text
                                token = event_data.get("text", "")
                                accumulated_text += token
                                
                                # Update the display
                                with response_placeholder.container():
                                    st.markdown(accumulated_text)
                                
                                # Small delay for smooth rendering
                                time.sleep(0.01)
                                
                            elif event_data.get("type") == "done":
                                # Streaming completed
                                break
                                
                            elif event_data.get("type") == "error":
                                # Handle streaming error
                                error_msg = event_data.get("message", "Unknown streaming error")
                                st.error(f"Streaming error: {error_msg}")
                                return None
                                
                        except json.JSONDecodeError:
                            # Skip malformed JSON
                            continue
                        except KeyError:
                            # Skip events without expected fields
                            continue
        
        # Clear the stop button
        if stop_button_placeholder:
            stop_button_placeholder.empty()
        
        # Final update with complete text
        if accumulated_text:
            with response_placeholder.container():
                st.markdown(accumulated_text)
        
        return accumulated_text if accumulated_text else None
        
    except httpx.TimeoutException:
        st.error("⏱️ Request timed out. Please check your backend connection and try again.")
        return None
    except httpx.ConnectError:
        st.error(f"🔌 Cannot connect to backend at {backend_url}. Please ensure the backend is running.")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return None

def main():
    """Main Streamlit application"""
    
    # Initialize session state
    initialize_session_state()
    
    # Main title
    st.markdown('<h1 class="main-header">RIVA ChatGPT</h1>', unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Model information (read-only)
        st.subheader("Model")
        st.info(f"**Current Model:**\n{MODEL_ID}")
        
        # Temperature slider
        st.subheader("Parameters")
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperature,
            step=0.1,
            help="Controls randomness in responses. Lower values make responses more focused and deterministic."
        )
        st.session_state.temperature = temperature
        
        # Max tokens input
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=1,
            max_value=4096,
            value=st.session_state.max_tokens,
            step=50,
            help="Maximum number of tokens to generate in the response."
        )
        st.session_state.max_tokens = max_tokens
        
        st.divider()
        
        # Backend configuration
        st.subheader("Backend")
        backend_url = st.text_input(
            "Backend URL",
            value=st.session_state.backend_url,
            help="URL of the RIVA ChatGPT API backend"
        )
        st.session_state.backend_url = backend_url
        
        st.divider()
        
        # Clear chat button
        if st.button("🗑️ Clear Chat", use_container_width=True):
            clear_chat()
        
        # Chat statistics
        if st.session_state.messages:
            st.subheader("📊 Chat Stats")
            user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
            assistant_messages = len([m for m in st.session_state.messages if m["role"] == "assistant"])
            st.metric("User Messages", user_messages)
            st.metric("Assistant Messages", assistant_messages)
    
    # Main chat area
    st.subheader("💬 Chat")
    
    # Display existing messages
    for message in st.session_state.messages:
        display_message(message["role"], message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to session state
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt
        })
        
        # Display user message
        display_message("user", prompt)
        
        # Stream assistant response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                # Stream response from backend
                response_text = stream_chat_response(
                    messages=st.session_state.messages,
                    temperature=st.session_state.temperature,
                    max_tokens=st.session_state.max_tokens,
                    backend_url=st.session_state.backend_url
                )
            
            # Add assistant message to history if we got a response
            if response_text:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text
                })
            else:
                # Add error message to history
                error_msg = "Sorry, I encountered an error processing your request. Please try again."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
    
    # Help information
    if not st.session_state.messages:
        st.markdown("""
        ### 👋 Welcome to RIVA ChatGPT!
        
        This is a minimal ChatGPT-like demo that uses:
        - **Frontend**: Streamlit for the chat interface
        - **Backend**: FastAPI with streaming responses
        - **AI Model**: Claude 3.5 Sonnet via AWS Bedrock
        
        **How to use:**
        1. Type your message in the chat input below
        2. Adjust temperature and max tokens in the sidebar if needed
        3. Click the "Clear Chat" button to start over
        
        **Current Status:**
        - ✅ UI Foundation (User Story #6) - **Complete**
        - ✅ Streaming Integration (User Story #7) - **Complete**
        - ⏳ Documentation (User Story #8) - **Coming Next**
        
        Start chatting by typing a message below! 👇
        """)

if __name__ == "__main__":
    main()