"""
Unit tests for the feedback producer service.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from google.cloud.pubsub_v1 import PublisherClient

from app import app
import app as app_module

# Test client
client = TestClient(app)

class TestFeedbackProducer:
    """Test cases for the feedback producer API."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_feedback = {
            "user_id": "user-123",
            "comment": "The new dashboard is visually appealing, but it's incredibly slow to load."
        }
        
        self.expected_response = {
            "success": True,
            "feedback_id": "fdbk-9a8b7c6d",
            "message": "Feedback submitted successfully"
        }
        
        # Set up global variables for testing
        app_module.project_id = "test-project"
        app_module.topic_name = "customer-feedback"
    
    @patch('app.publisher_client')
    def test_submit_feedback_success(self, mock_publisher):
        """Test successful feedback submission."""
        # Mock the publisher client
        mock_future = Mock()
        mock_future.result.return_value = "message-123"
        mock_publisher.publish.return_value = mock_future
        mock_publisher.topic_path.return_value = "projects/test-project/topics/customer-feedback"
        
        # Set the global publisher client
        app_module.publisher_client = mock_publisher
        
        # Test the endpoint
        response = client.post("/v1/feedback", json=self.sample_feedback)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "feedback_id" in data
        assert data["message"] == "Feedback submitted successfully"
        
        # Verify publisher was called
        mock_publisher.publish.assert_called_once()
    
    def test_submit_feedback_empty_comment(self):
        """Test feedback submission with empty comment."""
        feedback_data = {
            "user_id": "user-123",
            "comment": ""
        }
        
        response = client.post("/v1/feedback", json=feedback_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Comment cannot be empty" in data["detail"]
    
    def test_submit_feedback_whitespace_comment(self):
        """Test feedback submission with whitespace-only comment."""
        feedback_data = {
            "user_id": "user-123",
            "comment": "   "
        }
        
        response = client.post("/v1/feedback", json=feedback_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Comment cannot be empty" in data["detail"]
    
    def test_submit_feedback_missing_user_id(self):
        """Test feedback submission without user_id."""
        feedback_data = {
            "comment": "This is a test comment"
        }
        
        response = client.post("/v1/feedback", json=feedback_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_submit_feedback_long_comment(self):
        """Test feedback submission with comment exceeding max length."""
        feedback_data = {
            "user_id": "user-123",
            "comment": "x" * 5001  # Exceeds 5000 character limit
        }
        
        response = client.post("/v1/feedback", json=feedback_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.publisher_client')
    def test_submit_feedback_pubsub_error(self, mock_publisher):
        """Test feedback submission when Pub/Sub fails."""
        # Mock publisher to raise an exception
        mock_publisher.publish.side_effect = Exception("Pub/Sub error")
        mock_publisher.topic_path.return_value = "projects/test-project/topics/customer-feedback"
        
        # Set the global publisher client
        app_module.publisher_client = mock_publisher
        
        response = client.post("/v1/feedback", json=self.sample_feedback)
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to submit feedback" in data["detail"]
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "feedback-producer"
    
    def test_get_feedback_status(self):
        """Test get feedback status endpoint."""
        feedback_id = "fdbk-123"
        response = client.get(f"/v1/feedback/{feedback_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["feedback_id"] == feedback_id
        assert data["status"] == "submitted"
    
    def test_feedback_id_generation(self):
        """Test that feedback IDs are generated correctly."""
        response = client.post("/v1/feedback", json=self.sample_feedback)
        
        assert response.status_code == 200
        data = response.json()
        assert data["feedback_id"].startswith("fdbk-")
        assert len(data["feedback_id"]) == 13  # "fdbk-" + 8 hex chars
    
    def test_custom_feedback_id(self):
        """Test feedback submission with custom feedback_id."""
        feedback_data = {
            "feedback_id": "custom-fdbk-123",
            "user_id": "user-123",
            "comment": "This is a test comment"
        }
        
        response = client.post("/v1/feedback", json=feedback_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["feedback_id"] == "custom-fdbk-123"
    
    def test_timestamp_generation(self):
        """Test that timestamps are generated correctly."""
        with patch('app.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value.isoformat.return_value = "2025-01-01T12:00:00"
            
            response = client.post("/v1/feedback", json=self.sample_feedback)
            
            assert response.status_code == 200
            # Verify the timestamp was included in the published message
            # This would require mocking the publisher to capture the message content
    
    @patch('app.publisher_client')
    def test_message_content_structure(self, mock_publisher):
        """Test that the published message has the correct structure."""
        mock_future = Mock()
        mock_future.result.return_value = "message-123"
        mock_publisher.publish.return_value = mock_future
        mock_publisher.topic_path.return_value = "projects/test-project/topics/customer-feedback"
        
        # Set the global publisher client
        app_module.publisher_client = mock_publisher
        
        feedback_data = {
            "feedback_id": "test-fdbk-123",
            "user_id": "user-123",
            "comment": "Test comment"
        }
        
        response = client.post("/v1/feedback", json=feedback_data)
        
        assert response.status_code == 200
        
        # Verify the message was published with correct content
        call_args = mock_publisher.publish.call_args
        topic_path, message_bytes = call_args[0]
        
        # Decode and verify message content
        message_data = json.loads(message_bytes.decode('utf-8'))
        assert message_data["feedback_id"] == "test-fdbk-123"
        assert message_data["user_id"] == "user-123"
        assert message_data["comment"] == "Test comment"
        assert "timestamp" in message_data
