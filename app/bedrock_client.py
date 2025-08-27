# AWS Bedrock client integration
# RIVA ChatGPT - AWS Bedrock streaming client for Claude Sonnet

import os
import json
import logging
from typing import List, Dict, Generator, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

# Configure logging
logger = logging.getLogger(__name__)

# AWS Bedrock model configuration
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"
ANTHROPIC_VERSION = "bedrock-2023-05-31"
DEFAULT_REGION = "us-east-1"

class BedrockClientError(Exception):
    """Custom exception for Bedrock client errors"""
    pass

class BedrockStreamingError(Exception):
    """Custom exception for Bedrock streaming errors"""
    pass

def _get_bedrock_client():
    """
    Create and return a Bedrock runtime client with proper configuration.
    
    Returns:
        boto3.Client: Configured Bedrock runtime client
        
    Raises:
        BedrockClientError: If client creation fails
    """
    try:
        # Get AWS configuration from environment or defaults
        region = os.getenv('BEDROCK_REGION', os.getenv('AWS_REGION', DEFAULT_REGION))
        profile = os.getenv('AWS_PROFILE')
        
        logger.info(f"Initializing Bedrock client in region: {region}")
        
        # Create session with optional profile
        if profile:
            session = boto3.Session(profile_name=profile)
            logger.info(f"Using AWS profile: {profile}")
        else:
            session = boto3.Session()
            logger.info("Using default AWS credentials")
        
        # Create Bedrock runtime client
        client = session.client(
            'bedrock-runtime',
            region_name=region
        )
        
        logger.info("Bedrock client initialized successfully")
        return client
        
    except NoCredentialsError:
        error_msg = "AWS credentials not found. Please configure with 'aws configure' or set environment variables."
        logger.error(error_msg)
        raise BedrockClientError(error_msg)
    except ClientError as e:
        error_msg = f"Failed to create Bedrock client: {e}"
        logger.error(error_msg)
        raise BedrockClientError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error creating Bedrock client: {e}"
        logger.error(error_msg)
        raise BedrockClientError(error_msg)

def _format_messages_for_anthropic(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Format messages for Anthropic Claude API format.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        
    Returns:
        List[Dict]: Formatted messages for Anthropic API
    """
    formatted_messages = []
    
    for message in messages:
        # Ensure required fields
        if 'role' not in message or 'content' not in message:
            logger.warning(f"Skipping malformed message: {message}")
            continue
            
        # Validate role
        if message['role'] not in ['user', 'assistant', 'system']:
            logger.warning(f"Invalid role '{message['role']}', defaulting to 'user'")
            role = 'user'
        else:
            role = message['role']
            
        formatted_messages.append({
            'role': role,
            'content': str(message['content'])
        })
    
    logger.debug(f"Formatted {len(formatted_messages)} messages for Anthropic")
    return formatted_messages

def _create_bedrock_payload(messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
    """
    Create the request payload for Bedrock Anthropic model.
    
    Args:
        messages: List of formatted messages
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        
    Returns:
        str: JSON payload for Bedrock request
    """
    # Clamp temperature to valid range
    temperature = max(0.0, min(1.0, temperature))
    max_tokens = max(1, min(max_tokens, 4096))  # Reasonable upper limit
    
    payload = {
        "anthropic_version": ANTHROPIC_VERSION,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages
    }
    
    logger.debug(f"Created Bedrock payload: temperature={temperature}, max_tokens={max_tokens}, messages_count={len(messages)}")
    return json.dumps(payload)

def stream_chat(messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 500) -> Generator[str, None, None]:
    """
    Generator function to stream chat responses from AWS Bedrock Claude Sonnet.
    
    Args:
        messages: List of message objects with 'role' and 'content' keys
        temperature: Sampling temperature (0.0-1.0), default 0.2
        max_tokens: Maximum tokens to generate, default 500
        
    Yields:
        str: Text chunks from the Claude model response
        
    Raises:
        BedrockClientError: If client setup fails
        BedrockStreamingError: If streaming fails
    """
    if not messages:
        logger.warning("No messages provided to stream_chat")
        return
    
    logger.info(f"Starting chat stream with {len(messages)} messages, temp={temperature}, max_tokens={max_tokens}")
    
    try:
        # Get Bedrock client
        client = _get_bedrock_client()
        
        # Format messages for Anthropic
        formatted_messages = _format_messages_for_anthropic(messages)
        if not formatted_messages:
            logger.error("No valid messages after formatting")
            raise BedrockStreamingError("No valid messages provided")
        
        # Create request payload
        payload = _create_bedrock_payload(formatted_messages, temperature, max_tokens)
        
        # Invoke model with response stream
        logger.info(f"Invoking Bedrock model: {MODEL_ID}")
        response = client.invoke_model_with_response_stream(
            modelId=MODEL_ID,
            body=payload,
            contentType='application/json',
            accept='application/json'
        )
        
        # Process streaming response
        stream = response.get('body')
        if not stream:
            raise BedrockStreamingError("No response stream received from Bedrock")
        
        total_tokens = 0
        
        for event in stream:
            chunk = event.get('chunk')
            if chunk:
                try:
                    # Parse the chunk data
                    chunk_data = json.loads(chunk.get('bytes').decode())
                    
                    # Handle different event types
                    if chunk_data.get('type') == 'content_block_delta':
                        # Extract text from content block delta
                        delta = chunk_data.get('delta', {})
                        if delta.get('type') == 'text_delta':
                            text = delta.get('text', '')
                            if text:
                                total_tokens += len(text.split())  # Rough token count
                                logger.debug(f"Yielding text chunk: {text[:50]}...")
                                yield text
                    
                    elif chunk_data.get('type') == 'message_stop':
                        logger.info(f"Stream completed. Approximate tokens: {total_tokens}")
                        break
                        
                    elif chunk_data.get('type') == 'error':
                        error_msg = chunk_data.get('message', 'Unknown streaming error')
                        logger.error(f"Bedrock streaming error: {error_msg}")
                        raise BedrockStreamingError(f"Bedrock error: {error_msg}")
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse chunk: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing chunk: {e}")
                    continue
    
    except BedrockClientError:
        # Re-raise client errors as-is
        raise
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        
        logger.error(f"AWS Bedrock API error [{error_code}]: {error_msg}")
        
        if error_code == 'AccessDeniedException':
            raise BedrockStreamingError("Access denied to Bedrock model. Check your AWS permissions and model access.")
        elif error_code == 'ValidationException':
            raise BedrockStreamingError(f"Invalid request parameters: {error_msg}")
        elif error_code == 'ThrottlingException':
            raise BedrockStreamingError("Request rate limit exceeded. Please try again later.")
        else:
            raise BedrockStreamingError(f"Bedrock API error: {error_msg}")
            
    except BotoCoreError as e:
        logger.error(f"AWS SDK error: {e}")
        raise BedrockStreamingError(f"AWS SDK error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in stream_chat: {e}")
        raise BedrockStreamingError(f"Unexpected streaming error: {e}")

def test_bedrock_connection() -> bool:
    """
    Test the Bedrock connection and model access.
    
    Returns:
        bool: True if connection and model access is successful
    """
    try:
        logger.info("Testing Bedrock connection...")
        
        test_messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        # Try to get at least one response chunk
        for chunk in stream_chat(test_messages, temperature=0.1, max_tokens=10):
            logger.info(f"Connection test successful. First chunk: {chunk[:30]}...")
            return True
            
        logger.warning("Connection test completed but no chunks received")
        return False
        
    except Exception as e:
        logger.error(f"Bedrock connection test failed: {e}")
        return False

# Initialize logging for this module
logger.info("Bedrock client module loaded successfully")