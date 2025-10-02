"""
Feedback Producer Service
A FastAPI service that accepts customer feedback and publishes it to Google Cloud Pub/Sub.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import PublisherClient
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Customer Feedback Producer",
    description="API for accepting and publishing customer feedback to Pub/Sub",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class FeedbackRequest(BaseModel):
    """Request model for feedback submission."""
    feedback_id: str = Field(default_factory=lambda: f"fdbk-{uuid4().hex[:8]}")
    user_id: str = Field(..., description="Unique identifier for the user")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    comment: str = Field(..., min_length=1, max_length=5000, description="Customer feedback text")

class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""
    success: bool
    feedback_id: str
    message: str

# Global variables
publisher_client: PublisherClient = None
project_id: str = None
topic_name: str = None

@app.on_event("startup")
async def startup_event():
    """Initialize Pub/Sub client and configuration."""
    global publisher_client, project_id, topic_name
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    topic_name = os.getenv("PUBSUB_TOPIC", "customer-feedback")
    
    if not project_id:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT environment variable is required")
    
    try:
        publisher_client = pubsub_v1.PublisherClient()
        topic_path = publisher_client.topic_path(project_id, topic_name)
        
        # Verify topic exists
        try:
            publisher_client.get_topic(request={"topic": topic_path})
            logger.info(f"Connected to Pub/Sub topic: {topic_path}")
        except Exception as e:
            logger.error(f"Failed to connect to topic {topic_path}: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Failed to initialize Pub/Sub client: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources."""
    global publisher_client
    if publisher_client:
        publisher_client.close()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "feedback-producer"}

@app.post("/v1/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest) -> FeedbackResponse:
    """
    Submit customer feedback and publish to Pub/Sub.
    
    Args:
        feedback: Feedback data including user_id and comment
        
    Returns:
        FeedbackResponse with success status and feedback_id
        
    Raises:
        HTTPException: If publishing fails
    """
    try:
        # Validate feedback data
        if not feedback.comment.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment cannot be empty"
            )
        
        # Prepare message data
        message_data = {
            "feedback_id": feedback.feedback_id,
            "user_id": feedback.user_id,
            "timestamp": feedback.timestamp,
            "comment": feedback.comment.strip()
        }
        
        # Convert to JSON bytes
        message_json = json.dumps(message_data)
        message_bytes = message_json.encode("utf-8")
        
        # Publish to Pub/Sub
        topic_path = publisher_client.topic_path(project_id, topic_name)
        future = publisher_client.publish(topic_path, message_bytes)
        message_id = future.result()
        
        logger.info(f"Published feedback {feedback.feedback_id} to Pub/Sub with message ID: {message_id}")
        
        return FeedbackResponse(
            success=True,
            feedback_id=feedback.feedback_id,
            message="Feedback submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to publish feedback {feedback.feedback_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )

@app.get("/v1/feedback/{feedback_id}")
async def get_feedback_status(feedback_id: str):
    """
    Get the status of a submitted feedback (placeholder for future implementation).
    """
    return {
        "feedback_id": feedback_id,
        "status": "submitted",
        "message": "Feedback processing status endpoint (to be implemented)"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )
