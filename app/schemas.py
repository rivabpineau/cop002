# Pydantic schemas for request/response validation
# RIVA ChatGPT - API request and response models

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal, Union
from enum import Enum

class MessageRole(str, Enum):
    """Valid message roles for chat conversations"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class Message(BaseModel):
    """Chat message schema with validation"""
    role: MessageRole = Field(..., description="The role of the message sender")
    content: str = Field(..., min_length=1, max_length=32000, description="The message content")
    
    class Config:
        # Allow enum values to be serialized as strings
        use_enum_values = True
        
    @validator('content')
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty or whitespace only')
        return v.strip()

class ChatRequest(BaseModel):
    """Chat API request schema with comprehensive validation"""
    messages: List[Message] = Field(..., min_items=1, max_items=50, description="List of conversation messages")
    temperature: Optional[float] = Field(default=0.2, ge=0.0, le=1.0, description="Sampling temperature (0.0-1.0)")
    max_tokens: Optional[int] = Field(default=500, ge=1, le=4096, description="Maximum tokens to generate")
    stream: Optional[bool] = Field(default=True, description="Enable streaming response")
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError('At least one message is required')
        
        # Ensure conversation flow makes sense
        user_messages = [msg for msg in v if msg.role == MessageRole.USER]
        if not user_messages:
            raise ValueError('At least one user message is required')
            
        return v

class SSEEventType(str, Enum):
    """Server-Sent Event types for streaming responses"""
    TOKEN = "token"
    DONE = "done"
    ERROR = "error"
    HEARTBEAT = "heartbeat"

class SSETokenEvent(BaseModel):
    """SSE event for streaming text tokens"""
    type: Literal[SSEEventType.TOKEN] = SSEEventType.TOKEN
    text: str = Field(..., description="Text chunk from the AI response")

class SSEDoneEvent(BaseModel):
    """SSE event to signal completion of streaming"""
    type: Literal[SSEEventType.DONE] = SSEEventType.DONE

class SSEErrorEvent(BaseModel):
    """SSE event for error handling"""
    type: Literal[SSEEventType.ERROR] = SSEEventType.ERROR
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")

class SSEHeartbeatEvent(BaseModel):
    """SSE event for keeping connection alive"""
    type: Literal[SSEEventType.HEARTBEAT] = SSEEventType.HEARTBEAT
    timestamp: Optional[str] = Field(None, description="Heartbeat timestamp")

# Union type for all possible SSE events
SSEEvent = Union[SSETokenEvent, SSEDoneEvent, SSEErrorEvent, SSEHeartbeatEvent]

class ChatResponse(BaseModel):
    """Standard chat response (non-streaming)"""
    message: str = Field(..., description="The AI response message")
    model: str = Field(..., description="Model used for generation")
    tokens_used: Optional[int] = Field(None, description="Approximate tokens used")

class HealthResponse(BaseModel):
    """Health check response schema"""
    status: Literal["ok"] = "ok"
    
class ErrorResponse(BaseModel):
    """Standard error response schema"""
    detail: str = Field(..., description="Error description")
    code: Optional[str] = Field(None, description="Error code")
    type: Optional[str] = Field(None, description="Error type")