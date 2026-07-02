# Requirements Document

## Introduction

Sampark is an AI-powered Decision Intelligence Platform built for the Google ADK/LangChain hackathon. It enables citizens to report community issues, government officers to make data-driven resource decisions, and administrators to manage the AI knowledge base — all coordinated through a multi-agent LangGraph orchestration layer grounded in Gemini-powered RAG retrieval of government policies and municipal documents.

The platform covers the full lifecycle of a community issue: intake → validation → analytics → prediction → recommendation → workflow automation → citizen notification — with real-time dashboards surfacing Community Health Scores and predictive risk maps for government officers.

---

## Glossary

- **Platform**: The Sampark AI Decision Intelligence Platform as a whole
- **API_Gateway**: The FastAPI-based entry point that authenticates, validates, and routes all external requests
- **Supervisor**: The LangGraph Supervisor node that receives parsed requests from the API_Gateway and routes execution across agents
- **GraphState**: The shared state object that all LangGraph nodes read from and write to; fields include `query`, `user`, `location`, `issue`, `validation`, `analytics`, `prediction`, `recommendation`, `workflow`, and `response`
- **Intake_Agent**: The LangGraph node responsible for parsing natural language, voice, and image input into a structured issue object
- **Validation_Agent**: The LangGraph node that scores issue credibility, detects duplicates, and cross-references location evidence
- **Data_Intelligence_Agent**: The LangGraph node that queries BigQuery, Firestore, Weather, Maps, and Traffic data to populate raw context
- **Analytics_Agent**: The LangGraph node that performs trend detection, clustering, sentiment analysis, and outlier detection on gathered data
- **Prediction_Agent**: The LangGraph node that forecasts future risks (floods, road failure, garbage overflow, demand spikes) from historical and real-time data
- **Recommendation_Agent**: The LangGraph node that combines analytics, predictions, and RAG-retrieved policies to produce explainable, cited recommendations
- **Workflow_Agent**: The LangGraph node that automates department assignment, task creation, report generation, and escalation
- **Notification_Agent**: The LangGraph node that dispatches status updates to citizens via FCM, email, SMS, and WhatsApp
- **RAG_Pipeline**: The Retrieval-Augmented Generation subsystem that ingests government documents, embeds them, retrieves relevant chunks, and grounds Gemini responses
- **Vector_Store**: The Vertex AI Vector Search index holding document chunk embeddings for the RAG_Pipeline
- **Community_Health_Score**: A composite numeric score (0–100) computed per ward from infrastructure, sanitation, water, road, and traffic sub-scores
- **Citizen**: An end user who reports issues, uploads media, asks questions, and receives notifications
- **Government_Officer**: An end user who views dashboards, allocates resources, and queries AI for analytics
- **Community_Leader**: An end user who views ward-level trends and community health data
- **Admin**: An end user who manages the knowledge base, configures agents, and views system logs
- **Issue**: A structured record of a community problem with fields for type, location, description, media references, severity, and status
- **JWT**: JSON Web Token used for stateless authentication between the frontend and API_Gateway

---

## Requirements

---

### Requirement 1: Issue Intake via Natural Language, Voice, and Image

**User Story:** As a Citizen, I want to report a community issue using text, voice, or an image so that I can notify authorities without needing technical expertise.

#### Acceptance Criteria

1. WHEN a Citizen submits a text description via the chat interface, THE Intake_Agent SHALL extract `type`, `location`, and `description` fields and populate the `issue` field of GraphState within 5 seconds.
2. WHEN a Citizen uploads an audio file, THE Intake_Agent SHALL transcribe the audio using the Vertex AI Speech-to-Text API and populate the `type`, `location`, and `description` fields of GraphState's `issue` object within 15 seconds of upload.
3. IF the uploaded audio is inaudible, corrupt, or in an unsupported format, THEN THE Intake_Agent SHALL set an `intake_error` flag in GraphState with a reason code of `"audio_unprocessable"` and halt downstream routing.
4. WHEN a Citizen uploads an image, THE Intake_Agent SHALL generate a caption using the Vision API and include the caption and a Cloud Storage reference URI in the `issue` field of GraphState.
5. IF the Vision API cannot identify a recognizable community issue in the uploaded image, THEN THE Intake_Agent SHALL set an `intake_error` flag in GraphState with reason code `"image_unclassifiable"` and halt downstream routing.
6. WHEN the submitted text is in a language other than English, THE Intake_Agent SHALL detect the language, translate the content, and record the original language in GraphState.
7. IF the Intake_Agent cannot detect the language or the detected language is not supported for translation, THEN THE Intake_Agent SHALL preserve the original text in GraphState, set a `translation_error` flag, and continue processing using the original text.
8. IF the Intake_Agent cannot extract a recognizable location from the input, THEN THE Intake_Agent SHALL set the `issue.location` field to `null` and include an `extraction_error` flag in GraphState so the Supervisor can route to a clarification step.
9. WHEN a Citizen submits any issue via any input channel, THE Intake_Agent SHALL classify the issue into one of the predefined categories: `road`, `sanitation`, `water`, `electricity`, `flood`, `traffic`, `health`, or `other`.

---

### Requirement 2: Issue Validation and Credibility Scoring

**User Story:** As a Government Officer, I want submitted issues to be automatically validated so that I can trust the data before allocating resources.

#### Acceptance Criteria

1. WHEN the Validation_Agent receives an issue from GraphState, THE Validation_Agent SHALL query Firestore for existing open issues within 500 meters of the reported location; IF at least one such issue is found with the same `issue.type`, THEN THE Validation_Agent SHALL set `validation.duplicate` to `true`; OTHERWISE THE Validation_Agent SHALL set `validation.duplicate` to `false`.
2. WHEN the Validation_Agent receives an issue from GraphState, THE Validation_Agent SHALL compute a `confidence_score` between 0.0 and 1.0 based on corroborating evidence (nearby complaints, weather data, map verification) and write it to the `validation` field of GraphState.
3. IF the `confidence_score` is below 0.4, THEN THE Validation_Agent SHALL set `validation.status` to `"low_confidence"` so downstream agents can apply appropriate weight to the issue.
4. WHEN the `confidence_score` is 0.4 or above, THE Validation_Agent SHALL set `validation.status` to `"valid"`.
5. WHEN the Validation_Agent receives an issue from GraphState, THE Validation_Agent SHALL call the Maps Tool to verify that the reported location corresponds to a real address or coordinate within the configured geographic boundary.
6. WHEN the Maps Tool returns a valid location match, THE Validation_Agent SHALL set `validation.location_verified` to `true`.
7. IF the Maps Tool returns no valid location match, THEN THE Validation_Agent SHALL set `validation.location_verified` to `false` and record the failure reason in GraphState.
8. WHEN the Validation_Agent receives an issue from GraphState, THE Validation_Agent SHALL complete all validation checks (duplicate detection, confidence scoring, location verification) and write results to GraphState within 8 seconds.

---

### Requirement 3: Contextual Data Retrieval

**User Story:** As a Government Officer, I want the system to automatically gather relevant historical, environmental, and infrastructure data so that decisions are grounded in real context rather than just the citizen's report.

#### Acceptance Criteria

1. WHEN the Data_Intelligence_Agent is invoked, THE Data_Intelligence_Agent SHALL query BigQuery for historical issue records matching the same `issue.type` and ward-level location scope from the past 90 days and write the results to GraphState.
2. WHEN the Data_Intelligence_Agent is invoked, THE Data_Intelligence_Agent SHALL call the Weather Tool to retrieve current and 48-hour forecast data for the issue location and write the results to GraphState.
3. WHEN the Data_Intelligence_Agent is invoked, THE Data_Intelligence_Agent SHALL call the Maps Tool to retrieve traffic density, road classification, infrastructure category, and nearby facility tags for the issue location and write the results to GraphState.
4. THE Data_Intelligence_Agent SHALL complete all data retrieval operations within 10 seconds of invocation; if any source has not responded by that deadline, THE Data_Intelligence_Agent SHALL write a consolidated context object to GraphState with null values for the timed-out sources and continue.
5. IF any individual data source (BigQuery, Weather, Maps) returns an error response or does not respond within 5 seconds, THEN THE Data_Intelligence_Agent SHALL log the failure, set that source's field to `null` in GraphState, and continue retrieving from the remaining sources.

---

### Requirement 4: Analytics and Pattern Detection

**User Story:** As a Government Officer, I want the system to identify trends, clusters, and anomalies in community data so that I can prioritize systemic problems over isolated incidents.

#### Acceptance Criteria

1. WHEN the Analytics_Agent receives populated context from GraphState, THE Analytics_Agent SHALL compute the percentage change in complaint volume for the relevant `issue.type` and ward over the prior 7-day and 30-day windows relative to the preceding equivalent period; IF the baseline period contains zero complaints, THE Analytics_Agent SHALL set the percentage change to `null` and record a `zero_baseline` flag.
2. WHEN the Analytics_Agent receives populated context from GraphState, THE Analytics_Agent SHALL perform geospatial clustering to identify wards where complaint density exceeds 1.5 standard deviations above the citywide mean and write cluster labels and centroids to GraphState.
3. WHEN the Analytics_Agent receives populated context from GraphState, THE Analytics_Agent SHALL run sentiment analysis on citizen reports submitted in the affected ward within the past 30 days and write an aggregate sentiment score on a scale of -1.0 (most negative) to 1.0 (most positive) to GraphState.
4. THE Analytics_Agent SHALL detect and flag outlier issues whose combined z-score of `confidence_score` and complaint frequency exceeds 2.0 standard deviations above the ward mean.
5. IF the context provided to the Analytics_Agent contains fewer than 5 historical complaint records for the relevant ward and issue type, THEN THE Analytics_Agent SHALL set `analytics.insufficient_data` to `true`, skip trend and cluster computation, and write only the sentiment score and flag to GraphState.
6. THE Analytics_Agent SHALL write all analytics results to GraphState within 12 seconds of invocation.

---

### Requirement 5: Predictive Risk Forecasting

**User Story:** As a Government Officer, I want the system to forecast future community risks so that I can take preventive action before problems escalate.

#### Acceptance Criteria

1. WHEN the Prediction_Agent is invoked with populated analytics and weather context, THE Prediction_Agent SHALL compute a flood risk probability in the range 0.0–1.0 for the issue location using historical complaint patterns, rainfall forecast, and drainage records, and write it to `prediction.flood_risk` in GraphState.
2. WHEN the Prediction_Agent is invoked with populated analytics context, THE Prediction_Agent SHALL compute a road deterioration risk score in the range 0.0–1.0 for the issue location and write it to `prediction.road_risk` in GraphState.
3. WHEN the Prediction_Agent is invoked with populated analytics context, THE Prediction_Agent SHALL generate a 7-day complaint volume forecast per ward per issue category and write the forecast array to `prediction.volume_forecast` in GraphState.
4. IF `prediction.flood_risk` exceeds 0.75 OR `prediction.road_risk` exceeds 0.75, THEN THE Prediction_Agent SHALL set `prediction.high_risk_alert` to `true` in GraphState so the Supervisor can trigger priority escalation.
5. IF the Prediction_Agent is invoked with missing or null analytics or weather context, THEN THE Prediction_Agent SHALL set `prediction.error` to `"insufficient_context"` in GraphState and skip model execution.
6. THE Prediction_Agent SHALL write all predictions to GraphState within 15 seconds of invocation.
7. THE Prediction_Agent SHALL include an explainability object for each prediction that lists the top 3 contributing factors and their relative weights expressed as percentages summing to 100.

---

### Requirement 6: RAG-Grounded Policy Retrieval

**User Story:** As a Government Officer, I want AI recommendations to reference actual government policies and municipal regulations so that I can act on legally grounded, explainable advice.

#### Acceptance Criteria

1. THE RAG_Pipeline SHALL ingest PDF documents (Municipal Acts, Traffic Policy, Disaster SOP, Health Guidelines, Waste Management Rules) by splitting them into chunks of at most 512 tokens with a 64-token overlap, embedding each chunk using the Vertex AI text-embedding model, and storing the embeddings in the Vector_Store.
2. WHEN the Recommendation_Agent requires policy context, THE RAG_Pipeline SHALL retrieve the top 5 most semantically similar chunks from the Vector_Store for the given issue type and analytics summary; each returned chunk SHALL include the source document name and section heading (if available, otherwise page number) as citation metadata.
3. THE Recommendation_Agent SHALL use retrieved policy chunks and Gemini to generate a recommendation that explicitly cites at least one source document by name and section.
4. FOR ALL valid policy documents ingested by the RAG_Pipeline, encoding a document into the Vector_Store and then retrieving chunks using a verbatim sentence from that document SHALL return at least one chunk from the correct source document.
5. THE RAG_Pipeline SHALL produce a serialized representation of each ingested document's chunk list containing chunk index, document name, page number, token count, and chunk text; re-ingesting this representation SHALL produce chunks with identical boundaries, token counts, and metadata.
6. IF a PDF document fails to parse during ingestion, THEN THE RAG_Pipeline SHALL skip that document, record an error entry containing the document name and failure reason in the ingestion log, and continue processing remaining documents.
7. IF the Gemini generation step fails or times out, THEN THE RAG_Pipeline SHALL return an error response to the Recommendation_Agent without partial output.
8. IF a retrieval query returns zero results from the Vector_Store, THEN THE RAG_Pipeline SHALL return an empty list and set a `no_policy_context` flag so the Recommendation_Agent can generate a recommendation without policy grounding and disclose this to the user.

---

### Requirement 7: Explainable Recommendations

**User Story:** As a Government Officer, I want AI-generated recommendations to be explainable and actionable so that I can justify resource allocation decisions to stakeholders.

#### Acceptance Criteria

1. WHEN the Recommendation_Agent is invoked with analytics, prediction, and RAG context in GraphState, THE Recommendation_Agent SHALL produce a recommendation object containing: `action`, `priority` (Critical / High / Medium / Low), `rationale`, `cited_policies` (array), and `estimated_impact` fields.
2. IF `prediction.flood_risk` exceeds 0.75 OR `prediction.road_risk` exceeds 0.75, AND the affected area population density exceeds 5,000 persons per square kilometer, THEN THE Recommendation_Agent SHALL set `recommendation.priority` to `"Critical"`. IF only one of the two risk conditions is met, THE Recommendation_Agent SHALL set priority to `"High"`.
3. WHEN the `no_policy_context` flag is set in GraphState, THE Recommendation_Agent SHALL include a `disclaimer` field in the recommendation stating that no policy document was available to ground the recommendation.
4. THE Recommendation_Agent SHALL write the completed recommendation object to the `recommendation` field of GraphState within 20 seconds of invocation.
5. IF `validation.status` is `"low_confidence"` and the Recommendation_Agent would produce a priority of `"High"` or `"Critical"`, THEN THE Recommendation_Agent SHALL include `confidence_caveat: true` in the recommendation object.
6. IF the Recommendation_Agent does not complete within 20 seconds, THEN THE Supervisor SHALL mark the recommendation step as failed, set `recommendation.error` to `"timeout"` in GraphState, and route to an error response.

---

### Requirement 8: Workflow Automation and Department Assignment

**User Story:** As a Government Officer, I want issues to be automatically routed to the correct department with tasks created and notifications triggered so that I don't have to manually coordinate every complaint.

#### Acceptance Criteria

1. WHEN the Workflow_Agent receives a completed recommendation from GraphState, THE Workflow_Agent SHALL map the `issue.type` to the responsible department using the configured department routing table and write the `assigned_department` field to GraphState.
2. WHEN the Workflow_Agent assigns a department, THE Workflow_Agent SHALL create a task record in Firestore containing `issue_id`, `assigned_department`, `priority`, `due_date` (in UTC ISO 8601 format), and `status: "open"` within 3 seconds.
3. WHEN a task is created by the Workflow_Agent, THE Workflow_Agent SHALL publish a Pub/Sub event to the `task-created` topic so the Notification_Agent and dashboard update service can consume it asynchronously.
4. WHEN a task `priority` is `"Critical"`, THE Workflow_Agent SHALL set the `due_date` to 24 hours from creation; WHEN priority is `"High"`, THE Workflow_Agent SHALL set `due_date` to 72 hours; WHEN priority is `"Medium"` or `"Low"`, THE Workflow_Agent SHALL set `due_date` to 7 days.
5. WHEN an open task passes its `due_date` without a status update, THE Workflow_Agent SHALL escalate the task by incrementing its priority by one level (Low→Medium→High→Critical) and publishing a Pub/Sub escalation event; tasks already at `"Critical"` priority SHALL NOT be further escalated but SHALL re-publish the escalation event every 24 hours until resolved.
6. IF the department routing table does not contain a mapping for the given `issue.type`, THEN THE Workflow_Agent SHALL assign the task to the default `"Admin Review"` department and set a `routing_fallback` flag in GraphState.
7. IF the Firestore task creation fails, THEN THE Workflow_Agent SHALL retry once after 2 seconds; IF the retry also fails, THE Workflow_Agent SHALL set a `workflow_error` flag in GraphState and skip Pub/Sub publishing.
8. IF the Workflow_Agent fails to publish to the `task-created` Pub/Sub topic after the task record is successfully created in Firestore, THEN THE Workflow_Agent SHALL log the failure with the `task_id` and `issue_id` so the event can be manually replayed.

---

### Requirement 9: Citizen Notification Lifecycle

**User Story:** As a Citizen, I want to receive status updates at each stage of my reported issue so that I know my report was received and is being acted on.

#### Acceptance Criteria

1. WHEN a Pub/Sub `task-created` event is received by the Notification_Agent, THE Notification_Agent SHALL determine the Citizen's preferred channel from their Firestore profile; IF no preferred channel is stored, THE Notification_Agent SHALL default to email; THE Notification_Agent SHALL send a confirmation notification via the determined channel within 60 seconds.
2. WHEN a task status changes to `"in_progress"` in Firestore, THE Notification_Agent SHALL send an "Engineer Assigned" notification to the Citizen within 60 seconds of the status change event.
3. WHEN a task status changes to `"resolved"` in Firestore, THE Notification_Agent SHALL send a "Resolved" notification to the Citizen within 60 seconds.
4. WHEN a task is escalated by the Workflow_Agent, THE Notification_Agent SHALL notify the Citizen within 60 seconds; IF an assigned Government_Officer is recorded on the task, THE Notification_Agent SHALL also notify the Government_Officer within 60 seconds; IF no officer is assigned, THE Notification_Agent SHALL notify the `Admin Review` department distribution address instead.
5. IF a notification delivery fails on the primary channel after one retry attempt within 30 seconds, THEN THE Notification_Agent SHALL attempt delivery on the fallback channel (email if FCM or WhatsApp fails; SMS if email fails) within 120 seconds of the original attempt.
6. THE Notification_Agent SHALL log all notification attempts, delivery statuses, and failure reasons to Firestore under the `notifications` collection.

---

### Requirement 10: LangGraph Orchestration and State Management

**User Story:** As a developer, I want the multi-agent pipeline to be orchestrated by a stateful graph so that agent execution is deterministic, resumable, and observable.

#### Acceptance Criteria

1. WHEN the Supervisor receives a request with a known `issue.type` and `validation.status` is not `"low_confidence"`, THE Supervisor SHALL route execution to the standard pipeline (Data_Intelligence_Agent → parallel Analytics+Prediction → Recommendation_Agent → Workflow_Agent → Notification_Agent).
2. IF the Supervisor receives a request with an unrecognized `issue.type`, THEN THE Supervisor SHALL classify it as `"other"`, log the unrecognized value, and route to the standard pipeline.
3. WHEN the `issue.type` is known and `validation.status` is not `"low_confidence"`, THE Supervisor SHALL execute the Data_Intelligence_Agent, Analytics_Agent, and Prediction_Agent as parallel LangGraph nodes and merge their results into GraphState before invoking the Recommendation_Agent.
4. WHEN any parallel agent node (Data_Intelligence_Agent, Analytics_Agent, or Prediction_Agent) fails, THE Supervisor SHALL set that agent's GraphState fields to `null`, log the failure, and continue the pipeline with remaining agents' outputs rather than halting.
5. THE Platform SHALL persist each GraphState checkpoint to Firestore so that a failed or interrupted execution can be resumed from the last completed node without re-running earlier nodes.
6. WHEN any agent node raises an unhandled exception, THE Supervisor SHALL catch the exception, log it to Cloud Logging with the associated `session_id`, increment a retry counter in GraphState, wait 2 seconds, and retry the node up to 2 times before setting `execution.status` to `"failed"` in GraphState and returning an error response via the API_Gateway.
7. THE Platform SHALL stream partial GraphState updates to the connected API_Gateway client using Server-Sent Events; IF the client disconnects, THE Platform SHALL continue pipeline execution and persist final state to Firestore.
8. THE Platform SHALL complete the full pipeline from Intake_Agent to Notification_Agent dispatch within 60 seconds for 95% of requests when system load does not exceed 100 concurrent active sessions and no external dependencies are degraded.

---

### Requirement 11: API Gateway — Authentication, Validation, and Routing

**User Story:** As a developer, I want a secure, rate-limited API gateway so that the platform is protected from abuse and all requests are authenticated before reaching the agent pipeline.

#### Acceptance Criteria

1. THE API_Gateway SHALL require a JWT in the `Authorization: Bearer` header for all endpoints except `/auth/login` and `/health`; a valid JWT is one that passes signature verification against the configured signing key, has a non-expired `exp` claim, and contains a `user_id` claim.
2. IF the JWT is missing, has an invalid signature, is expired, or is missing a required claim, THEN THE API_Gateway SHALL return HTTP 401 with a JSON error body containing `code` and `message` fields without forwarding the request.
3. THE API_Gateway SHALL track request counts per authenticated `user_id` within a fixed 60-second sliding window.
4. IF a user's request count exceeds 60 within the current window, THEN THE API_Gateway SHALL return HTTP 429 with a `Retry-After` header set to the whole number of seconds remaining until the current window expires.
5. WHEN a client establishes a connection to the `GET /chat/stream/{session_id}` endpoint, THE API_Gateway SHALL open a Server-Sent Events stream and forward agent progress updates for the specified session to the client until the pipeline completes or the client disconnects.
6. IF no active session exists for the requested `session_id` on the `GET /chat/stream/{session_id}` endpoint, THEN THE API_Gateway SHALL return HTTP 404 with a JSON error body.
7. WHEN a request body fails schema validation, THE API_Gateway SHALL return HTTP 422 with a JSON error body listing each invalid field and its violation.
8. THE API_Gateway SHALL log every inbound request with `timestamp`, `user_id`, `endpoint`, `http_method`, `status_code`, and `latency_ms` (measured from receipt of first byte to completion of last response byte) to Cloud Logging.

---

### Requirement 12: Community Health Score Computation

**User Story:** As a Government Officer, I want a composite Community Health Score per ward so that I can benchmark wards and track improvement over time.

#### Acceptance Criteria

1. THE Platform SHALL compute a Community Health Score for each ward on a 0–100 scale using a weighted average of sub-scores: Infrastructure (25%), Sanitation (20%), Water (20%), Road (20%), and Traffic (15%); IF a sub-score is unavailable for a ward, THE Platform SHALL rebalance the remaining sub-score weights proportionally so that all available weights still sum to 100%.
2. WHEN the Community Health Score for a ward transitions from 60 or above to below 60 during a recompute cycle, THE Platform SHALL flag the ward as `"At Risk"` in the BigQuery `community_scores` table and trigger a Pub/Sub alert event.
3. WHEN the Community Health Score for a ward transitions from below 60 to 60 or above during a recompute cycle, THE Platform SHALL remove the `"At Risk"` flag from the ward's record in the BigQuery `community_scores` table.
4. WHEN a scheduled Cloud Function triggers the 24-hour recompute cycle, THE Platform SHALL recompute Community Health Scores for all wards and store the results in BigQuery; IF the BigQuery write fails, THE Platform SHALL retain the last known scores and log the failure.
5. WHEN the `GET /analytics/ward/{ward_id}/health-score` endpoint is called with a valid `ward_id`, THE Platform SHALL return the Community Health Score history for that ward for the last 90 days; IF the `ward_id` does not exist, THE Platform SHALL return HTTP 404.
6. WHEN the Analytics_Agent is computing issue priority, THE Analytics_Agent SHALL use the Community Health Score recorded within the past 25 hours for the affected ward as an input feature; IF no score within that window exists, THE Analytics_Agent SHALL omit the Community Health Score from priority computation and set an `analytics.health_score_unavailable` flag.

---

### Requirement 13: Dashboard and Data Visualization

**User Story:** As a Government Officer, I want real-time dashboards showing community health, predictions, and department performance so that I can make informed decisions without running manual queries.

#### Acceptance Criteria

1. THE Platform SHALL expose a Looker Studio-compatible BigQuery view (`sampark_dashboard_view`) that contains complaint volume, Community Health Scores, prediction risk levels, and department resolution rates aggregated by ward and date; the view SHALL be queryable without additional joins or transformations.
2. WHEN a Government_Officer accesses the dashboard, THE Platform SHALL display the most recently computed Community Health Score, a risk heatmap, a 7-day complaint trend chart, and the top 5 open issues with priority `"Critical"` for their authorized ward scope.
3. THE Platform SHALL render the dashboard initial page load within 3 seconds for a dataset of up to 100,000 complaint records under normal load conditions.
4. WHEN a Community_Leader accesses the dashboard, THE Platform SHALL restrict the visible data to the wards listed in the Community_Leader's `ward_ids` JWT claim; IF a request targets a ward not in that list, THE Platform SHALL return HTTP 403.
5. WHILE a Government_Officer is viewing the live dashboard, THE Platform SHALL push real-time task status updates to the browser via Server-Sent Events within 5 seconds of a status change event, without requiring a page refresh.

---

### Requirement 14: Knowledge Base Management

**User Story:** As an Admin, I want to upload, update, and delete policy documents from the RAG knowledge base so that the AI recommendations remain current with the latest regulations.

#### Acceptance Criteria

1. WHEN an Admin uploads a PDF document (maximum 50 MB) via the `POST /admin/knowledge-base` endpoint, THE Platform SHALL store the file in Cloud Storage, trigger the RAG_Pipeline ingestion process, and return a `document_id` within 5 seconds of request receipt.
2. WHEN an Admin deletes a document via the `DELETE /admin/knowledge-base/{document_id}` endpoint, THE Platform SHALL remove the document from Cloud Storage and delete all associated embeddings from the Vector_Store within 30 seconds.
3. WHEN an Admin uploads a document using an existing `document_id`, THE Platform SHALL confirm deletion of all previous embeddings from the Vector_Store before beginning ingestion of the new version.
4. IF a non-Admin user sends a request to any `/admin/*` endpoint, THEN THE Platform SHALL reject the request with an authorization failure response without processing the request body.
5. THE Platform SHALL maintain an audit log in Firestore recording each knowledge base operation (upload, delete, update) with `timestamp`, `admin_user_id`, `document_id`, and `action`.
6. IF the RAG_Pipeline ingestion fails after file storage, THEN THE Platform SHALL delete the uploaded file from Cloud Storage, return an error response to the Admin, and log the failure with the document name and reason.
7. IF deletion of embeddings from the Vector_Store fails, THEN THE Platform SHALL retain the file in Cloud Storage, return an error response indicating partial failure, and log the failure without marking the document as deleted.

---

### Requirement 15: Multi-Channel Input — WhatsApp and Voice

**User Story:** As a Citizen, I want to report issues through WhatsApp or voice so that I can use channels I am already comfortable with, without needing to install a separate app.

#### Acceptance Criteria

1. WHEN a WhatsApp message is received via the configured webhook endpoint, THE API_Gateway SHALL verify the webhook signature using the configured HMAC secret; IF the signature is valid, THE API_Gateway SHALL extract the message text and any attached media and forward the payload to the Supervisor within 3 seconds.
2. IF the webhook signature is invalid or absent, THEN THE API_Gateway SHALL return HTTP 403 and discard the message without forwarding it.
3. WHEN a voice message not exceeding 10 MB or 5 minutes in duration is received via WhatsApp or the Voice API endpoint, THE Intake_Agent SHALL transcribe the audio and produce a structured issue object using the same pipeline as a text submission.
4. IF the voice message exceeds 10 MB or 5 minutes, or if transcription fails, THEN THE Intake_Agent SHALL set `intake_error` to `"voice_unprocessable"` in GraphState and halt downstream routing.
5. WHEN a Citizen submits a report via WhatsApp, THE Notification_Agent SHALL send all subsequent status notifications for that issue via WhatsApp using the same sender number.
6. IF the WhatsApp webhook delivery response is not sent within 15 seconds, THEN THE API_Gateway SHALL return HTTP 200 to the WhatsApp provider to prevent retry floods and enqueue the message internally for asynchronous processing.

---

### Requirement 16: Security, Authentication, and Role-Based Access Control

**User Story:** As an Admin, I want all platform resources to be protected by role-based access control so that users can only access data and operations appropriate to their role.

#### Acceptance Criteria

1. THE Platform SHALL enforce the following role-based permissions: `citizen` may create and read their own complaints and notifications; `government_officer` may read all complaints, tasks, analytics, and predictions within their assigned ward_ids and update task status; `community_leader` may read complaints, analytics, and Community Health Scores within their ward_ids; `admin` may perform all operations including knowledge base management, user management, and system configuration.
2. WHEN a user sends valid credentials to `POST /auth/login`, THE API_Gateway SHALL return a JWT with a 24-hour expiry containing `user_id`, `role`, and `ward_ids` claims; IF the credentials are invalid, THE API_Gateway SHALL return an authentication failure response without revealing whether the username or password was incorrect.
3. THE Platform SHALL store all user passwords as bcrypt hashes with a minimum cost factor of 12 and SHALL NOT store plaintext passwords.
4. IF a request arrives over plaintext HTTP, THEN THE Platform SHALL reject it without processing.
5. THE API_Gateway SHALL strip or reject any user-provided input containing prompt injection patterns (e.g., instruction-override sequences, role-reassignment tokens) before passing the input to the Supervisor or any agent; IF injection is detected, THE API_Gateway SHALL return an error response and log the attempt.
6. WHERE Google Cloud Secret Manager is configured, THE Platform SHALL retrieve all API keys, database credentials, and service account tokens from Secret Manager rather than environment variables or source code.
7. IF a JWT is presented that was issued before the user's last password change timestamp, THEN THE API_Gateway SHALL treat the token as expired and return HTTP 401.

---

### Requirement 17: Deployment, Scalability, and Observability

**User Story:** As a developer, I want the platform deployed on Google Cloud Run with CI/CD and observability so that it can scale automatically and issues can be diagnosed quickly.

#### Acceptance Criteria

1. THE Platform SHALL be containerized using Docker with a multi-stage build producing a production image under 1 GB in size.
2. WHEN the number of concurrent requests per Cloud Run instance exceeds 30, THE Platform SHALL scale out to additional instances; THE Platform SHALL reach at least 10 running instances within 60 seconds of sustained load above this threshold.
3. THE Platform SHALL emit structured JSON logs to Cloud Logging for every agent invocation, tool call, GraphState transition, and API request; each log entry SHALL include at minimum: `timestamp`, `severity`, `event_type`, and `trace_id`.
4. THE Platform SHALL expose a `GET /health` endpoint that returns HTTP 200 with a JSON body indicating the health status of the API_Gateway, Firestore connection, BigQuery connection, and Vector_Store connection when all dependencies are reachable.
5. IF one or more health dependencies are unreachable, THEN the `GET /health` endpoint SHALL return HTTP 503 with a JSON body identifying each failing dependency by name.
6. WHEN a pull request is merged to the `main` branch, THE Platform SHALL run the full test suite, build the Docker image, and deploy to Cloud Run; IF any test fails, the deployment step SHALL be skipped and the CI pipeline SHALL report a failure.
7. WHERE Cloud Monitoring is configured, THE Platform SHALL publish custom metrics: `agent_latency_ms` (integer milliseconds), `pipeline_success_rate` (float 0.0–1.0), and `rag_retrieval_hit_rate` (float 0.0–1.0) so that SLA compliance can be tracked in dashboards.

---

### Requirement 18: Data Persistence and Schema

**User Story:** As a developer, I want well-defined data schemas across Firestore, BigQuery, and Cloud Storage so that data is consistent, queryable, and maintainable.

#### Acceptance Criteria

1. THE Platform SHALL store all active user sessions, complaints, task records, and notifications in Firestore using the collections: `users`, `complaints`, `tasks`, `sessions`, and `notifications`; each document SHALL include a `created_at` and `updated_at` timestamp field.
2. THE Platform SHALL store all historical analytics results, community health score time series, prediction outputs, and aggregated reports in BigQuery under the `sampark_analytics` dataset; each table row SHALL include a `ward_id`, `issue_type`, and `computed_at` field to support time-series queries.
3. WHEN a Citizen uploads an image or audio file, THE Platform SHALL store the file in Cloud Storage under the path `media/{issue_id}/{filename}`, generate a signed URI with a 7-day expiry, and write the signed URI to the associated Firestore complaint document.
4. THE Platform SHALL enforce Firestore security rules that prevent `citizen` role users from reading or writing documents outside the `complaints` and `notifications` collections scoped to their own `user_id`; attempts to access other collections SHALL be rejected without error details.
5. THE Platform SHALL define a composite index on the `complaints` Firestore collection on `(ward_id, issue_type, created_at)` to support query performance of under 1 second for the Analytics_Agent on datasets up to 500,000 documents.

