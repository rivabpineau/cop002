# FastAPI main application
# RIVA ChatGPT Backend API

import logging
import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
import uvicorn

# Import our schemas and bedrock client
from .schemas import (
    ChatRequest, ChatResponse, HealthResponse, ErrorResponse,
    SSETokenEvent, SSEDoneEvent, SSEErrorEvent, SSEHeartbeatEvent,
    Message, MessageRole
)
from .bedrock_client import stream_chat, BedrockClientError, BedrockStreamingError, MODEL_ID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="RIVA ChatGPT API",
    description="A minimal ChatGPT-like demo with streaming responses using AWS Bedrock",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:*",
        "http://127.0.0.1:*", 
        "http://localhost:8501",  # Streamlit default port
        "http://localhost:3000",  # Common dev port
        "http://localhost:8080",  # Common dev port
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception handler caught: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check endpoint
@app.get("/health", 
         summary="Health Check",
         description="Check if the API server is running and healthy",
         response_description="API health status")
async def health_check():
    """
    Health check endpoint that returns the status of the API server.
    
    Returns:
        dict: Status information indicating the server is healthy
    """
    logger.info("Health check requested")
    return {"status": "ok"}

# Root endpoint  
@app.get("/",
         summary="API Root",
         description="Root endpoint with API information")
async def root():
    """
    Root endpoint providing basic API information.
    
    Returns:
        dict: Basic API information and status
    """
    return {
        "message": "RIVA ChatGPT API",
        "version": "1.0.0",
        "description": "A minimal ChatGPT-like demo with streaming responses",
        "docs": "/docs",
        "health": "/health"
    }

# Helper function to format SSE events
def format_sse_event(event_data: dict) -> str:
    """
    Format data as Server-Sent Event.
    
    Args:
        event_data: Dictionary to send as SSE event
        
    Returns:
        str: Properly formatted SSE event string
    """
    return f"data: {json.dumps(event_data)}\n\n"

# Streaming chat endpoint
@app.post("/chat",
          summary="Streaming Chat with AI",
          description="Send messages to AI and receive streaming responses via Server-Sent Events",
          response_description="Server-Sent Events stream with AI responses")
async def chat_stream(request: ChatRequest, http_request: Request):
    """
    Streaming chat endpoint that accepts conversation messages and returns
    real-time AI responses via Server-Sent Events.
    
    Args:
        request: Chat request with messages and parameters
        http_request: HTTP request object for connection monitoring
        
    Returns:
        StreamingResponse: SSE stream with AI responses
    """
    logger.info(f"Chat request received: {len(request.messages)} messages, temp={request.temperature}, max_tokens={request.max_tokens}")
    
    async def generate_chat_stream() -> AsyncGenerator[str, None]:
        """Generate the SSE stream for chat responses"""
        
        heartbeat_interval = 30  # Send heartbeat every 30 seconds
        last_heartbeat = datetime.now()
        
        try:
            # Convert Pydantic models to dict format for bedrock client
            messages_dict = [
                {"role": msg.role, "content": msg.content} 
                for msg in request.messages
            ]
            
            logger.info(f"Starting Bedrock stream with model: {MODEL_ID}")
            
            # Start streaming from Bedrock
            token_count = 0
            for text_chunk in stream_chat(
                messages=messages_dict,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            ):
                # Check if client disconnected
                if await http_request.is_disconnected():
                    logger.info("Client disconnected, stopping stream")
                    break
                
                # Send text token event
                if text_chunk:
                    token_event = SSETokenEvent(text=text_chunk)
                    yield format_sse_event(token_event.dict())
                    token_count += 1
                    
                    # Send periodic heartbeat
                    current_time = datetime.now()
                    if (current_time - last_heartbeat).seconds >= heartbeat_interval:
                        heartbeat_event = SSEHeartbeatEvent(timestamp=current_time.isoformat())
                        yield format_sse_event(heartbeat_event.dict())
                        last_heartbeat = current_time
                
                # Small delay to prevent overwhelming the connection
                await asyncio.sleep(0.01)
            
            # Send completion event
            done_event = SSEDoneEvent()
            yield format_sse_event(done_event.dict())
            
            logger.info(f"Chat stream completed successfully. Tokens sent: {token_count}")
            
        except BedrockClientError as e:
            logger.error(f"Bedrock client error: {e}")
            error_event = SSEErrorEvent(
                message="Failed to connect to AI service. Please check your AWS configuration.",
                code="BEDROCK_CLIENT_ERROR"
            )
            yield format_sse_event(error_event.dict())
            
        except BedrockStreamingError as e:
            logger.error(f"Bedrock streaming error: {e}")
            error_event = SSEErrorEvent(
                message=f"AI service error: {str(e)}",
                code="BEDROCK_STREAMING_ERROR"
            )
            yield format_sse_event(error_event.dict())
            
        except ValidationError as e:
            logger.error(f"Request validation error: {e}")
            error_event = SSEErrorEvent(
                message="Invalid request format. Please check your message format.",
                code="VALIDATION_ERROR"
            )
            yield format_sse_event(error_event.dict())
            
        except asyncio.CancelledError:
            logger.info("Stream cancelled by client")
            # Don't send error event for cancellation
            
        except Exception as e:
            logger.error(f"Unexpected error in chat stream: {e}")
            error_event = SSEErrorEvent(
                message="An unexpected error occurred. Please try again.",
                code="INTERNAL_ERROR"
            )
            yield format_sse_event(error_event.dict())
    
    # Return streaming response
    return StreamingResponse(
        generate_chat_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Application startup event
@app.on_event("startup")
async def startup_event():
    logger.info("RIVA ChatGPT API server starting up...")
    logger.info("Server is ready to accept requests")

# Application shutdown event  
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("RIVA ChatGPT API server shutting down...")

if __name__ == "__main__":
    # Run the server directly if this file is executed
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )