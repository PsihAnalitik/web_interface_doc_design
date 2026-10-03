**Company**: Salesforce
**Title**: How We Built the First Dreamforce Event Agent in 5 Days with Agentforce
**Technology Area**: AI agents
**Source URL**: https://www.salesforce.com/blog/build-an-ai-agent/
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The project was initiated one week before Dreamforce 2023, Salesforce's largest annual event. The goal was to create an AI agent, named "Ask Astro," to be integrated natively into the Salesforce Events mobile app. The agent was designed to assist event attendees by providing information and performing actions on their behalf. This effort was a migration of a pre-existing homegrown agent to Salesforce's internal Agentforce stack.

#### 1.2. Relevance & reasons

The primary motivation was to enhance the Dreamforce attendee experience by providing an intelligent, interactive assistant within the event app. The agent would help users find information, manage their schedules, and discover relevant sessions, replacing a more cumbersome manual search or a less integrated AI solution.

A key business driver was to showcase the capabilities of Salesforce's own AI platform, specifically Agentforce Service Agent and Data Cloud RAG. The project served as a practical demonstration of the message, "Don’t DIY your AI," highlighting the productivity, configurability, and debugging advantages of the Salesforce stack over open-source alternatives.

#### 1.3. Expectations

The agent was expected to:
*   Live natively within the Salesforce Events app.
*   Answer user questions grounded in event data (FAQs, session schedules).
*   Take actions on behalf of the user, such as managing their event schedule.
*   Recommend sessions based on user queries, time, and other factors.

#### 1.4. Previous work

A "homegrown AI agent" had been previously developed by the Marketing Event Tech team over the course of a month. This initial version was built using:
*   OpenAI function-calling.
*   A vector database hosted on Heroku.

This system was considered "daunting" to test and tune due to frequent feature requests and content updates, which prompted the migration to the more integrated Agentforce platform.

#### 1.5. Usage volumes and patterns

The system was designed for attendees of Dreamforce, Salesforce's "biggest event of the year." While specific QPS or user counts are not provided, the context implies a large, high-concurrency user base for a short period (the duration of the event).

### 2. Goals and anti-goals

#### 2.1. Goals

*   Successfully migrate the homegrown AI agent to the Agentforce and Data Cloud stack within 5 days, before the start of Dreamforce.
*   Provide attendees with a tool to find information from FAQs and session data.
*   Enable the agent to manage user schedules by taking actions.
*   Improve search accuracy, particularly for speaker names.
*   Improve the configurability, debugging ability, and overall developer productivity compared to the previous open-source stack.
*   Use the agent as a real-world showcase for Agentforce and Data Cloud RAG capabilities.

#### 2.2. Anti-goals

*   **Do-It-Yourself (DIY) AI:** The project explicitly aimed to move away from a difficult-to-maintain open-source stack, embodying the principle "Don't DIY your AI."
*   **Complex Backend Logic for Simple Tasks:** For the MVP, complex time zone conversion logic was intentionally avoided in the backend Apex code. Instead, the problem was solved via prompt engineering, instructing the LLM to handle the conversion.

### 3. Risks and constraints

*   **Extreme Time Constraint:** The entire migration and deployment had to be completed in 5 days, just before Dreamforce went live.
*   **Production Environment Limitations:** The production environment where the agent ran did not yet have the latest no-code "Retriever" feature sets. This forced the engineering team to write a custom Apex class to call the Data Cloud query-service connect API directly, adding implementation overhead.
*   **Data Freshness:** Session schedules and speaker bios could change, requiring a solution for periodically refreshing the search index to avoid providing stale information to attendees.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Qualitative Feedback:** The team relied on iterative, qualitative feedback from teammates in Slack. An early version was described as "80% there."
*   **Search Accuracy:** A key focus was improving "speaker name accuracy." The success of the hybrid search and augmented indexing was validated by testing specific name queries (e.g., "Adam Evans") and ensuring the correct sessions were returned.

#### 4.2. Online/business metrics

*   **User Interaction Tracking:** The system used "Einstein feedback" to track how attendees interacted with the Ask Astro Agent. This data was collected to understand user behavior and identify areas for improvement in the FAQ content and agent capabilities for future events like World Tour or TDX.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Session Data:** A CSV file (`all-dreamforce-sessions.csv`) containing all Dreamforce session information, including session types, abstracts, and speaker names.
*   **FAQ Data:** A spreadsheet of frequently asked questions, which was later migrated into Salesforce Knowledge articles.
*   **Streaming Session Updates:** A vendor's session API provided real-time updates to session schedules and speaker information.

#### 5.2. Labeling strategy

[NO INFO]

#### 5.3. Data quality issues and cleaning/enrichment

*   **Poor Speaker Name Salience:** The speaker's name was a small part of the overall session text, leading to poor retrieval accuracy with vector search alone. For example, a search for "Adam Evans" might return sessions by other people named Adam or Evans.
*   **Time Zone Mismatch:** Session data was provided in UTC, which was not user-friendly for attendees in Pacific Time. This was initially addressed via prompt engineering rather than data transformation.
*   **Data Transformation for Streaming:** The JSON output from the vendor's session API had to be converted into the format required by the Data Cloud Ingestion API. An LLM was used to help generate the necessary Java code for this JSON processing in 45 minutes.

#### 5.4. ETL

*   **Initial Batch Ingestion:** The `all-dreamforce-sessions.csv` file was ingested into Data Cloud by creating a data model directly from the CSV.
*   **Streaming Ingestion Pipeline:**
    1.  A recurring pipeline was built using **Mulesoft Anypoint Studio**.
    2.  The pipeline calls the vendor's session API every 5 minutes [inferred from diagram].
    3.  A Java process transforms the API's JSON output into the desired format.
    4.  The transformed data is sent to the **Data Cloud Ingestion API**.
    5.  This feeds a **Data Stream** in Data Cloud (with DLO to DMO mapping), which supports change-data capturing.
    6.  Changes in the data stream are synced to the search index in near real-time.

### 6. Validation schema

*   **Iterative Testing:** The validation process was ad-hoc and iterative. An MVP was built and shared in Slack for team members to test and provide feedback.
*   **Dedicated Test Agent:** A separate `Robert Test Agent` was created to replicate the topics and actions of the main `Ask Astro Agent`. This allowed for isolated testing of the new Data Cloud-based retrieval action (`retrieveSessions_DataCloud`) without affecting the main agent.
*   **Specific Query Validation:** The team verified functionality by running specific test queries, such as "Marc Benioff’s sessions on Tuesday," and checking that the agent selected the correct topic (`Session management`), action (`Retrieve Sessions from DataCloud`), and passed the correct parameters (`searchTerm`, `startsBetween`).
*   **End-to-End Pipeline Validation:** To test the streaming update pipeline, the team removed some speakers from the vendor system and added themselves as test speakers, then searched for their own names to confirm the changes were propagated through the entire system to the search index.

### 7. Baseline solution

The baseline was the pre-existing "homegrown AI agent" developed by the Marketing Event Tech team.

*   **Architecture:** It used OpenAI for function calling and a vector database hosted on Heroku for retrieval.
*   **Integration:** The agent's retrieval capability was exposed as an agent action via an Apex class that made API calls to the Heroku-hosted service.
*   **Deficiencies:** The solution was considered "daunting" to test and tune. Frequent feature requests and content updates made maintenance difficult, motivating the migration to the more integrated and manageable Agentforce stack.

### 8. Errors and their analysis

*   **Error Type 1: Low-Precision Speaker Search**
    *   **Analysis:** Vector search alone was insufficient for finding speakers accurately. Because a speaker's name was a small, low-salience part of the vectorized session description, queries for specific names returned semantically related but incorrect results (e.g., other speakers with similar first or last names).
    *   **Resolution:** Implemented **Hybrid Search**, a beta feature in Data Cloud that combines semantic vector search with precise keyword search. This provided the "best of both worlds," improving lexical matching for names.

*   **Error Type 2: Ambiguous Name Matching**
    *   **Analysis:** Even with hybrid search, distinguishing between similar names (e.g., "Adam" vs. "Adams") remained a challenge.
    *   **Resolution:** Implemented **Augmented Indexing**. This involved creating smaller, specialized data chunks for each speaker, formatted like `Adam Evans, SVP, AI Platform Cloud, Salesforce`. These chunks were optimized to receive a high keyword score for name queries. When a query matched an augmented chunk, the system retrieved the full session information associated with it to pass to the LLM.

*   **Error Type 3: Incorrect Time Zone Display**
    *   **Analysis:** The backend data source provided session times in UTC, and the agent initially presented these times directly to the user, who was in Pacific Time.
    *   **Resolution:** A product manager implemented a "prompt magic" solution. An instruction was added to the action's description: `"Times for sessions are returned in UTC time. Always reformat them into Pacific Time (am/pm)"`. This delegated the time zone conversion logic to the LLM at generation time, avoiding a backend code change.

### 9. Training pipelines

The system is a RAG agent, so the "pipeline" concerns data indexing and agent configuration rather than model training.

*   **Tooling:**
    *   **Data Ingestion:** Mulesoft Anypoint Studio, Data Cloud Ingestion API.
    *   **Data Transformation:** Java (with code generated by an LLM for JSON processing).
    *   **Data Indexing:** Data Cloud vector/hybrid index.
    *   **Agent Logic:** Apex for custom actions (with LLM-assisted code generation).
    *   **Agent Configuration:** Agentforce Agent Builder.
*   **Automation and CI/CD:**
    *   The debugging cycle using Agent Builder was very short, around 30 seconds, enabling rapid iteration on prompts and configurations.
    *   The FAQ knowledge base could be updated through the Salesforce Lighting Knowledge UI, with a "Rebuild Index" button to manually trigger re-indexing.
    *   Session data was automatically updated via the Mulesoft streaming pipeline.

### 10. Features

The "features" in this RAG system are the documents and data chunks stored in the search index.

*   **Feature Categories:**
    *   **Session Information:** Full descriptions of Dreamforce sessions, including abstracts, types, and speaker details, vectorized for semantic search.
    *   **FAQ Knowledge Articles:** Content from FAQ spreadsheets converted into Salesforce Knowledge articles, indexed for question answering.
    *   **Augmented Speaker Chunks:** Small, derived text chunks containing only speaker information (name, title, company) to improve keyword matching for speaker-specific queries.
*   **Feature Computation (Indexing):**
    *   Data is ingested into Data Cloud from CSV files and streaming APIs.
    *   A **hybrid search index** is created in Data Cloud, combining vector search and keyword search capabilities.
    *   The index is enhanced with **augmented indexing**, where specialized chunks are created to optimize for specific query types (e.g., search by speaker name).
    *   The index supports near real-time updates via Data Cloud's streaming data functionality.

### 11. Measuring results

#### 11.1. Offline evaluation

Evaluation was primarily qualitative and iterative. The team tested the agent with specific queries and shared results in Slack. An early MVP was deemed "80% there" based on this informal feedback. Success was determined by verifying that the agent correctly identified the user's intent (topic), selected the right tool (action), and passed the correct parameters to the backend.

#### 11.2. A/B testing

[NO INFO]

#### 11.3. Reporting

*   **Development Phase:** Progress and test results were communicated via Slack.
*   **Production Phase:** The team enabled "Einstein feedback" to collect and analyze attendee interactions with the agent. This feedback serves as a report on agent performance and user needs, informing improvements for future events.

### 12. Integration and Serving

*   **Architecture Overview:** The Ask Astro Agent is composed of several components within the Salesforce ecosystem. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_035/img_015.png`)
    1.  **Client:** The agent is surfaced in the Salesforce Events mobile app, which communicates with the agent via a **Bot API**.
    2.  **Agent Orchestrator:** The **Agentforce** platform, powered by the **Atlas Reasoning Engine**, receives user utterances. It performs topic modeling to understand intent (e.g., "SessionManagement", "General Questions") and selects the appropriate action.
    3.  **Actions/Tools:** The agent has access to a set of tools:
        *   **Session Retrieval:** A custom Apex class (`retrieveSessions_DataCloud`) that calls the **Data Cloud Query Service**. This service uses a **Hybrid Search Re-ranker** to find the most relevant sessions from the index.
        *   **FAQ Answering:** The built-in `Answer Questions with Knowledge` action queries the indexed knowledge articles.
        *   **Schedule Management:** An invocable action framework is used to update a user's schedule.
    4.  **Data Layer:** **Data Cloud** stores and indexes both the session data (in a hybrid index) and the FAQ data (as knowledge articles).
*   **API Design:** The system uses a `Bot API` to connect the mobile app to the agent. Internal actions are implemented as Apex classes that call other Salesforce APIs, such as the `query-service connect API` for Data Cloud.
*   **SLAs & Latency:** [NO INFO]
*   **Fallback Strategies:** [NO INFO]

### 13. Monitoring

*   **Model & Business Quality Monitoring:** "Einstein feedback" was enabled to track attendee interactions, usage patterns, and qualitative performance. This data is used to identify areas for improving FAQ content and agent functionality for subsequent events.
*   **Data Quality & Pipeline Monitoring:** The streaming data pipeline was monitored manually during development by injecting test data (adding/removing speakers) and verifying that the search index updated correctly. The pipeline itself was configured for recurring runs to ensure data freshness.
*   **Engineering Metrics:** [NO INFO]
*   **Alerting:** [NO INFO]

### 14. Operations

*   **Retraining/Re-indexing Cadence:**
    *   **Session Data:** The search index for session data is updated in "near real time." A Mulesoft pipeline fetches new data every 5 minutes [inferred from diagram], and Data Cloud's streaming update capability syncs the changes to the index.
    *   **FAQ Data:** The FAQ knowledge base is updated manually. The Marketing Event Tech team can edit articles in the Salesforce Lighting Knowledge interface and then click a "Rebuild Index" button to trigger a refresh of the agent's knowledge.
*   **Ownership:**
    *   The **Marketing Event Tech team** owns the management of FAQ content.
    *   The **engineering team** owns the agent logic, data pipelines, and underlying infrastructure.
*   **Incident Response & Rollback:** The system was designed for rapid iteration. The debugging cycle with Agent Builder was as short as 30 seconds, allowing for quick fixes through prompt adjustments and configuration changes. No formal rollback procedures are mentioned.