"""
Unit tests for the feedback pipeline consumer.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from google.cloud import pubsub_v1, spanner, bigquery
from google.cloud.pubsub_v1.subscriber.message import Message

from consumer import FeedbackProcessor

class TestFeedbackProcessor:
    """Test cases for the feedback processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_feedback_data = {
            "feedback_id": "fdbk-123",
            "user_id": "user-456",
            "timestamp": "2025-01-01T12:00:00Z",
            "comment": "The new dashboard is visually appealing, but it's incredibly slow to load."
        }
        
        self.sample_ai_result = {
            "sentiment": "NEGATIVE",
            "topics": ["PERFORMANCE", "UI_UX"]
        }
        
        self.sample_message_data = json.dumps(self.sample_feedback_data).encode('utf-8')
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_initialization(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test processor initialization."""
        with patch.dict('os.environ', {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'PUBSUB_SUBSCRIPTION': 'test-subscription',
            'SPANNER_INSTANCE_ID': 'test-instance',
            'SPANNER_DATABASE_ID': 'test-db',
            'BIGQUERY_DATASET_ID': 'test-dataset',
            'BIGQUERY_TABLE_ID': 'test-table',
            'VERTEXAI_LOCATION': 'us-central1'
        }):
            processor = FeedbackProcessor()
            
            assert processor.project_id == 'test-project'
            assert processor.subscription_name == 'test-subscription'
            assert processor.spanner_instance_id == 'test-instance'
            assert processor.spanner_database_id == 'test-db'
            assert processor.bigquery_dataset_id == 'test-dataset'
            assert processor.bigquery_table_id == 'test-table'
            assert processor.vertexai_location == 'us-central1'
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_analyze_feedback_with_ai_success(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test successful AI analysis."""
        # Mock the model
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = '{"sentiment": "NEGATIVE", "topics": ["PERFORMANCE", "UI_UX"]}'
        mock_model.generate_content.return_value = mock_response
        mock_vertexai.GenerativeModel.return_value = mock_model
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.model = mock_model
            
            result = processor._analyze_feedback_with_ai("Test comment")
            
            assert result["sentiment"] == "NEGATIVE"
            assert result["topics"] == ["PERFORMANCE", "UI_UX"]
            mock_model.generate_content.assert_called_once()
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_analyze_feedback_with_ai_invalid_sentiment(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test AI analysis with invalid sentiment."""
        # Mock the model with invalid sentiment
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = '{"sentiment": "INVALID", "topics": ["PERFORMANCE"]}'
        mock_model.generate_content.return_value = mock_response
        mock_vertexai.GenerativeModel.return_value = mock_model
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.model = mock_model
            
            result = processor._analyze_feedback_with_ai("Test comment")
            
            assert result["sentiment"] == "NEUTRAL"  # Should default to NEUTRAL
            assert result["topics"] == ["PERFORMANCE"]
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_analyze_feedback_with_ai_invalid_json(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test AI analysis with invalid JSON response."""
        # Mock the model with invalid JSON
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = 'Invalid JSON response'
        mock_model.generate_content.return_value = mock_response
        mock_vertexai.GenerativeModel.return_value = mock_model
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.model = mock_model
            
            result = processor._analyze_feedback_with_ai("Test comment")
            
            assert result["sentiment"] == "NEUTRAL"
            assert result["topics"] == []
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_analyze_feedback_with_ai_exception(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test AI analysis with exception."""
        # Mock the model to raise an exception
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("AI service error")
        mock_vertexai.GenerativeModel.return_value = mock_model
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.model = mock_model
            
            result = processor._analyze_feedback_with_ai("Test comment")
            
            assert result["sentiment"] == "NEUTRAL"
            assert result["topics"] == []
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_store_raw_feedback_success(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test successful raw feedback storage in Spanner."""
        # Mock Spanner database
        mock_database = Mock()
        mock_spanner_client = Mock()
        mock_spanner_client.instance.return_value.database.return_value = mock_database
        mock_spanner.Client.return_value = mock_spanner_client
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.spanner_database = mock_database
            
            result = processor._store_raw_feedback(self.sample_feedback_data)
            
            assert result is True
            mock_database.run_in_transaction.assert_called_once()
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_store_raw_feedback_failure(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test raw feedback storage failure."""
        # Mock Spanner database to raise exception
        mock_database = Mock()
        mock_database.run_in_transaction.side_effect = Exception("Spanner error")
        mock_spanner_client = Mock()
        mock_spanner_client.instance.return_value.database.return_value = mock_database
        mock_spanner.Client.return_value = mock_spanner_client
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.spanner_database = mock_database
            
            result = processor._store_raw_feedback(self.sample_feedback_data)
            
            assert result is False
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_store_enriched_feedback_success(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test successful enriched feedback storage in BigQuery."""
        # Mock BigQuery client
        mock_bigquery_client = Mock()
        mock_bigquery_client.insert_rows_json.return_value = []  # No errors
        mock_bigquery.Client.return_value = mock_bigquery_client
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.bigquery_client = mock_bigquery_client
            processor.bigquery_table_ref = Mock()
            
            result = processor._store_enriched_feedback("fdbk-123", self.sample_ai_result)
            
            assert result is True
            mock_bigquery_client.insert_rows_json.assert_called_once()
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_store_enriched_feedback_failure(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test enriched feedback storage failure."""
        # Mock BigQuery client to return errors
        mock_bigquery_client = Mock()
        mock_bigquery_client.insert_rows_json.return_value = [{"error": "BigQuery error"}]
        mock_bigquery.Client.return_value = mock_bigquery_client
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.bigquery_client = mock_bigquery_client
            processor.bigquery_table_ref = Mock()
            
            result = processor._store_enriched_feedback("fdbk-123", self.sample_ai_result)
            
            assert result is False
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_process_message_success(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test successful message processing."""
        # Mock all dependencies
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = '{"sentiment": "NEGATIVE", "topics": ["PERFORMANCE"]}'
        mock_model.generate_content.return_value = mock_response
        mock_vertexai.GenerativeModel.return_value = mock_model
        
        mock_database = Mock()
        mock_spanner_client = Mock()
        mock_spanner_client.instance.return_value.database.return_value = mock_database
        mock_spanner.Client.return_value = mock_spanner_client
        
        mock_bigquery_client = Mock()
        mock_bigquery_client.insert_rows_json.return_value = []
        mock_bigquery.Client.return_value = mock_bigquery_client
        
        # Create mock message
        mock_message = Mock(spec=Message)
        mock_message.data = self.sample_message_data
        mock_message.ack = Mock()
        mock_message.nack = Mock()
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.model = mock_model
            processor.spanner_database = mock_database
            processor.bigquery_client = mock_bigquery_client
            processor.bigquery_table_ref = Mock()
            
            result = processor._process_message(mock_message)
            
            assert result is True
            mock_message.ack.assert_called_once()
            mock_database.run_in_transaction.assert_called_once()
            mock_bigquery_client.insert_rows_json.assert_called_once()
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_process_message_invalid_json(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test message processing with invalid JSON."""
        # Create mock message with invalid JSON
        mock_message = Mock(spec=Message)
        mock_message.data = b'Invalid JSON'
        mock_message.ack = Mock()
        mock_message.nack = Mock()
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            
            result = processor._process_message(mock_message)
            
            assert result is False
            mock_message.nack.assert_called_once()
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_process_message_spanner_failure(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test message processing when Spanner storage fails."""
        # Mock Spanner to fail
        mock_database = Mock()
        mock_database.run_in_transaction.side_effect = Exception("Spanner error")
        mock_spanner_client = Mock()
        mock_spanner_client.instance.return_value.database.return_value = mock_database
        mock_spanner.Client.return_value = mock_spanner_client
        
        # Create mock message
        mock_message = Mock(spec=Message)
        mock_message.data = self.sample_message_data
        mock_message.ack = Mock()
        mock_message.nack = Mock()
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.spanner_database = mock_database
            
            result = processor._process_message(mock_message)
            
            assert result is False
            mock_message.nack.assert_called_once()
    
    @patch('consumer.vertexai')
    @patch('consumer.pubsub_v1.SubscriberClient')
    @patch('consumer.spanner.Client')
    @patch('consumer.bigquery.Client')
    def test_process_message_bigquery_failure(self, mock_bigquery, mock_spanner, mock_pubsub, mock_vertexai):
        """Test message processing when BigQuery storage fails."""
        # Mock Spanner to succeed
        mock_database = Mock()
        mock_spanner_client = Mock()
        mock_spanner_client.instance.return_value.database.return_value = mock_database
        mock_spanner.Client.return_value = mock_spanner_client
        
        # Mock BigQuery to fail
        mock_bigquery_client = Mock()
        mock_bigquery_client.insert_rows_json.return_value = [{"error": "BigQuery error"}]
        mock_bigquery.Client.return_value = mock_bigquery_client
        
        # Mock AI model
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = '{"sentiment": "NEGATIVE", "topics": ["PERFORMANCE"]}'
        mock_model.generate_content.return_value = mock_response
        mock_vertexai.GenerativeModel.return_value = mock_model
        
        # Create mock message
        mock_message = Mock(spec=Message)
        mock_message.data = self.sample_message_data
        mock_message.ack = Mock()
        mock_message.nack = Mock()
        
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            processor.model = mock_model
            processor.spanner_database = mock_database
            processor.bigquery_client = mock_bigquery_client
            processor.bigquery_table_ref = Mock()
            
            result = processor._process_message(mock_message)
            
            assert result is False
            mock_message.nack.assert_called_once()
    
    def test_ai_prompt_template(self):
        """Test that the AI prompt template is correctly formatted."""
        with patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'}):
            processor = FeedbackProcessor()
            
            # Test prompt formatting
            test_comment = "Test feedback comment"
            formatted_prompt = processor.ai_prompt.format(feedback_text=test_comment)
            
            assert test_comment in formatted_prompt
            assert "POSITIVE" in formatted_prompt
            assert "NEGATIVE" in formatted_prompt
            assert "NEUTRAL" in formatted_prompt
            assert "BILLING" in formatted_prompt
            assert "UI_UX" in formatted_prompt
            assert "PERFORMANCE" in formatted_prompt
            assert "FEATURE_REQUEST" in formatted_prompt
