"""
AI-Powered Feedback Pipeline Consumer
Processes customer feedback from Pub/Sub, stores in Spanner, enriches with AI, and stores in BigQuery.
"""

import json
import logging
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
from datetime import datetime

import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud import pubsub_v1, spanner, bigquery
from google.cloud.spanner_v1 import types as spanner_types
from google.cloud.bigquery import SchemaField
import google.auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackProcessor:
    """Main class for processing feedback messages."""
    
    def __init__(self):
        """Initialize the feedback processor with GCP clients."""
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.subscription_name = os.getenv("PUBSUB_SUBSCRIPTION", "customer-feedback-sub")
        self.spanner_instance_id = os.getenv("SPANNER_INSTANCE_ID", "feedback-instance")
        self.spanner_database_id = os.getenv("SPANNER_DATABASE_ID", "feedback-db")
        self.bigquery_dataset_id = os.getenv("BIGQUERY_DATASET_ID", "feedback_analysis")
        self.bigquery_table_id = os.getenv("BIGQUERY_TABLE_ID", "feedback_analysis")
        self.vertexai_location = os.getenv("VERTEXAI_LOCATION", "us-central1")
        
        # Initialize GCP clients
        self._initialize_clients()
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.vertexai_location)
        self.model = GenerativeModel("gemini-1.5-flash")
        
        # AI prompt template
        self.ai_prompt = """
        Analyze the following customer feedback and return a JSON response with sentiment and topics.
        
        Sentiment options: POSITIVE, NEGATIVE, NEUTRAL
        Topic options: BILLING, UI_UX, PERFORMANCE, FEATURE_REQUEST
        
        Input: {feedback_text}
        
        Output JSON format:
        {{
            "sentiment": "<POSITIVE|NEGATIVE|NEUTRAL>",
            "topics": ["<topic1>", "<topic2>", "<topic3>"]
        }}
        
        Return only the JSON response, no additional text.
        """
        
        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Graceful shutdown handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self.shutdown_requested = False
    
    def _initialize_clients(self):
        """Initialize GCP service clients."""
        try:
            # Pub/Sub client
            self.subscriber = pubsub_v1.SubscriberClient()
            self.subscription_path = self.subscriber.subscription_path(
                self.project_id, self.subscription_name
            )
            
            # Spanner client
            self.spanner_client = spanner.Client()
            self.spanner_instance = self.spanner_client.instance(self.spanner_instance_id)
            self.spanner_database = self.spanner_instance.database(self.spanner_database_id)
            
            # BigQuery client
            self.bigquery_client = bigquery.Client()
            self.bigquery_table_ref = self.bigquery_client.dataset(
                self.bigquery_dataset_id
            ).table(self.bigquery_table_id)
            
            logger.info("Successfully initialized GCP clients")
            
        except Exception as e:
            logger.error(f"Failed to initialize GCP clients: {e}")
            raise
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    def _analyze_feedback_with_ai(self, comment: str) -> Dict[str, Any]:
        """
        Analyze feedback using Vertex AI Gemini model.
        
        Args:
            comment: The feedback comment text
            
        Returns:
            Dict containing sentiment and topics
        """
        try:
            prompt = self.ai_prompt.format(feedback_text=comment)
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse JSON response
            ai_result = json.loads(response_text)
            
            # Validate sentiment
            valid_sentiments = ["POSITIVE", "NEGATIVE", "NEUTRAL"]
            if ai_result.get("sentiment") not in valid_sentiments:
                logger.warning(f"Invalid sentiment: {ai_result.get('sentiment')}, defaulting to NEUTRAL")
                ai_result["sentiment"] = "NEUTRAL"
            
            # Validate topics
            valid_topics = ["BILLING", "UI_UX", "PERFORMANCE", "FEATURE_REQUEST"]
            topics = ai_result.get("topics", [])
            if not isinstance(topics, list):
                topics = []
            
            # Filter valid topics and limit to 3
            valid_topics_list = [t for t in topics if t in valid_topics][:3]
            ai_result["topics"] = valid_topics_list
            
            logger.info(f"AI analysis completed: sentiment={ai_result['sentiment']}, topics={ai_result['topics']}")
            return ai_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {"sentiment": "NEUTRAL", "topics": []}
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {"sentiment": "NEUTRAL", "topics": []}
    
    def _store_raw_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        """
        Store raw feedback in Cloud Spanner.
        
        Args:
            feedback_data: The feedback data to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            def insert_feedback(transaction):
                transaction.insert_or_update(
                    "raw_feedback",
                    columns=["feedback_id", "user_id", "timestamp", "comment", "created_at"],
                    values=[
                        (
                            feedback_data["feedback_id"],
                            feedback_data["user_id"],
                            feedback_data["timestamp"],
                            feedback_data["comment"],
                            datetime.utcnow().isoformat() + "Z"
                        )
                    ]
                )
            
            self.spanner_database.run_in_transaction(insert_feedback)
            logger.info(f"Stored raw feedback {feedback_data['feedback_id']} in Spanner")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store raw feedback in Spanner: {e}")
            return False
    
    def _store_enriched_feedback(self, feedback_id: str, ai_result: Dict[str, Any]) -> bool:
        """
        Store enriched feedback in BigQuery.
        
        Args:
            feedback_id: The feedback ID
            ai_result: AI analysis result
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare row data
            row_data = {
                "feedback_id": feedback_id,
                "sentiment": ai_result["sentiment"],
                "topics": ai_result["topics"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Insert row
            errors = self.bigquery_client.insert_rows_json(
                self.bigquery_table_ref, [row_data]
            )
            
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
                return False
            
            logger.info(f"Stored enriched feedback {feedback_id} in BigQuery")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store enriched feedback in BigQuery: {e}")
            return False
    
    def _process_message(self, message: pubsub_v1.subscriber.message.Message) -> bool:
        """
        Process a single feedback message.
        
        Args:
            message: Pub/Sub message
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Parse message data - use message.message.data for the new API
            feedback_data = json.loads(message.message.data.decode('utf-8'))
            feedback_id = feedback_data["feedback_id"]
            comment = feedback_data["comment"]
            
            logger.info(f"Processing feedback {feedback_id}")
            
            # Store raw feedback in Spanner
            if not self._store_raw_feedback(feedback_data):
                logger.error(f"Failed to store raw feedback {feedback_id}")
                return False
            
            # Analyze with AI
            ai_result = self._analyze_feedback_with_ai(comment)
            
            # Store enriched feedback in BigQuery
            if not self._store_enriched_feedback(feedback_id, ai_result):
                logger.error(f"Failed to store enriched feedback {feedback_id}")
                return False
            
            # Acknowledge message - use message.ack_id for the new API
            self.subscriber.acknowledge(
                request={"subscription": self.subscription_path, "ack_ids": [message.ack_id]}
            )
            logger.info(f"Successfully processed feedback {feedback_id}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message data: {e}")
            # Nack message - use message.ack_id for the new API
            self.subscriber.modify_ack_deadline(
                request={
                    "subscription": self.subscription_path, 
                    "ack_ids": [message.ack_id],
                    "ack_deadline_seconds": 0
                }
            )
            return False
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            # Nack message - use message.ack_id for the new API
            self.subscriber.modify_ack_deadline(
                request={
                    "subscription": self.subscription_path, 
                    "ack_ids": [message.ack_id],
                    "ack_deadline_seconds": 0
                }
            )
            return False
    
    def start_consuming(self):
        """Start consuming messages from Pub/Sub."""
        logger.info(f"Starting to consume messages from {self.subscription_path}")
        
        try:
            logger.info("Started polling for messages...")
            
            # Keep the main thread alive and poll for messages
            while not self.shutdown_requested:
                try:
                    # Pull messages synchronously
                    response = self.subscriber.pull(
                        request={"subscription": self.subscription_path, "max_messages": 10}
                    )
                    
                    if response.received_messages:
                        logger.info(f"Received {len(response.received_messages)} messages")
                        for message in response.received_messages:
                            self._process_message(message)
                    else:
                        # No messages, sleep briefly
                        time.sleep(1)
                        
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt")
                    break
                except Exception as e:
                    logger.error(f"Error during message processing: {e}")
                    time.sleep(5)  # Wait before retrying
                    
        except Exception as e:
            logger.error(f"Failed to start consuming: {e}")
            raise
        finally:
            self.executor.shutdown(wait=True)
            logger.info("Consumer shutdown complete")

def main():
    """Main entry point for the consumer."""
    try:
        processor = FeedbackProcessor()
        processor.start_consuming()
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
