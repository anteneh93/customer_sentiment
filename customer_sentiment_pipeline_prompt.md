# AI Prompt 

You are a senior Python and cloud engineer. Generate a complete, production-ready solution for a Google Cloud real-time feedback pipeline with AI enrichment based on the following requirements:

---

**Overview:**
Build a data pipeline to process customer feedback in real-time. The pipeline should:
1. Accept feedback from a REST API (simulated producer).
2. Publish feedback to a Google Cloud Pub/Sub topic.
3. Store raw feedback in Cloud Spanner.
4. Enrich feedback using Vertex AI Gemini model:
   - Sentiment analysis (POSITIVE, NEGATIVE, NEUTRAL)
   - Topic extraction (up to 3 from: BILLING, UI_UX, PERFORMANCE, FEATURE_REQUEST)
5. Store enriched feedback in BigQuery.
6. Run the pipeline consumer on GKE as a scalable, containerized app.
7. Include unit tests mocking Pub/Sub, Spanner, BigQuery, and Vertex AI.

---

**Deliverables:**

1. **Feedback Producer (/producer)**
   - Python REST API using FastAPI or Flask.
   - POST /v1/feedback endpoint that accepts JSON payloads.
   - Publishes the feedback to Pub/Sub topic `customer-feedback`.
   - Include Dockerfile, requirements.txt, and unit tests.

2. **AI-Powered Pipeline Consumer (/pipeline)**
   - Python service that:
     - Subscribes to `customer-feedback` Pub/Sub topic.
     - Writes raw feedback to Cloud Spanner table `raw_feedback`.
     - Calls Vertex AI Gemini model to analyze the comment text.
       - Return JSON with fields: `sentiment` and `topics`.
     - Writes enriched feedback to BigQuery table `feedback_analysis` with schema:
       - `feedback_id`, `sentiment`, `topics`, `timestamp`
   - Include Dockerfile, requirements.txt, and unit tests mocking all external services.

3. **Kubernetes (/k8s)**
   - Deployment manifest (`deployment.yaml`) for GKE.
   - Service manifest (`service.yaml`) for the consumer service.

4. **Terraform (/terraform)**
   - Deploy all required GCP infrastructure:
     - GKE cluster
     - Pub/Sub topic
     - Cloud Spanner instance & table
     - BigQuery dataset & table
     - IAM roles for service accounts (including Vertex AI access)

5. **CI/CD (.github/workflows/deploy.yml)**
   - GitHub Actions workflow:
     - Build and test Python services.
     - Push Docker images to Artifact Registry.
     - Apply Terraform and Kubernetes manifests.

6. **AI Prompt Usage**
   - Include the prompt used for Vertex AI Gemini:
     ```
     Input: feedback text
     Output: JSON { "sentiment": <POSITIVE|NEGATIVE|NEUTRAL>, "topics": [<topics>] }
     ```
   - Show example feedback input and expected JSON output.

---

**Example Feedback Input JSON:**
{
  "feedback_id": "fdbk-9a8b7c6d",
  "user_id": "user-789",
  "timestamp": "2025-09-29T13:00:00Z",
  "comment": "The new dashboard is visually appealing, but it's incredibly slow to load the main widgets. Also, I think there's an issue with how my latest invoice is calculated in the billing section."
}

**Expected AI JSON Output:**
{
  "sentiment": "NEGATIVE",
  "topics": ["PERFORMANCE", "BILLING"]
}

---

**Requirements for the generated code:**
- Python 3.11+, FastAPI or Flask
- Containerized services with Docker
- Terraform IaC for GCP resources
- Kubernetes manifests for GKE deployment
- Unit tests with pytest
- Proper error handling, logging, and modular code structure
- Clear directory structure: /producer, /pipeline, /k8s, /terraform

Generate all code files, directory structure, Dockerfiles, Terraform, Kubernetes manifests, and GitHub Actions workflow based on these requirements.

