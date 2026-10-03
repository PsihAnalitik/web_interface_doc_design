- Company: Airtable
- Title: Building a Resilient Embedding System for Semantic Search at Airtable
- Technology area: Generative AI & LLM
- Source URL: https://medium.com/airtable-eng/building-a-resilient-embedding-system-for-semantic-search-at-airtable-d5fdf27807e2
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The project was initiated by a small team of engineers at Airtable following the public emergence of ChatGPT in 2022. The core idea was to leverage new generative AI capabilities to enable rich, semantic search over customer data stored within the Airtable platform. This allows users to query their data using natural language questions about similarity and meaning, rather than just keywords.

#### 1.2. Relevance & reasons

The system aims to replace hours of manual labor required to find insights within large datasets. By using embeddings, teams can quickly identify relevant information. Example use cases include:
- A marketing team asking, “Can you find past campaigns similar to this one?”
- A product management team asking, “Can you find engineers whose expertise matches this project?”
- An internal support team asking, “Can you find past issues (called “escalations” internally) similar to this one?”

The existing flow for these tasks involves manual review and analysis, which is slow and inefficient. An embedding-powered system automates this process, unlocking insights that would otherwise be too time-consuming to discover.

#### 1.3. Expectations

The primary expectation is to build a system that is not just functional but also "robust and adaptable." This implies a strong focus on operational resilience, maintainability, and the ability to evolve with changing technologies (e.g., new models, vector databases). During a full data migration ("reset"), the downtime for the semantic search feature is expected to be minimal, with a p99.9 of under 2 minutes.

#### 1.4. Previous work

The primary baseline being improved upon is the manual process of users searching and analyzing their data, which can take hours. No prior automated or heuristic-based semantic search systems are mentioned.

#### 1.5. Usage volumes and patterns

The system is designed for a multi-tenant environment, handling "many collections" of embeddings. This requires a design that can scale in the number of partitions. No specific QPS, user counts, or data volumes are provided.

### 2. Goals and anti-goals

#### 2.1. Goals

- **Build a resilient and adaptable embedding system:** The system must gracefully handle a wide range of failures, migrations, and operational changes.
- **Enable semantic search:** Provide the capability to search customer data based on semantic meaning, not just keywords.
- **Support future evolution:** The design must accommodate changes in AI models, embedding providers, storage engines, and data schemas.
- **Ensure data security and compliance:** Treat embeddings as sensitive customer data and support requirements like data residency migrations (e.g., US to EU).

#### 2.2. Anti-goals

- **Full consistency:** The system explicitly avoids strong consistency between the primary database and the vector store. This was rejected due to prohibitive cost and performance implications.
- **Storing embeddings in the primary database:** Storing large embedding vectors in the main in-memory database (MemApp) was ruled out as it would be too expensive. Embeddings are often 10x the size of the underlying data.
- **Synchronous embedding generation:** Generating embeddings within transactions was rejected as it would be too slow for bulk updates and would limit the choice of models to less capable in-house ones. The system favors using top-tier external providers like OpenAI asynchronously.

### 3. Risks and constraints

#### 3.1. Technical Risks

The system is designed to mitigate a wide range of risks and failure modes, including:
- **Vector Database Failures:**
    - **Corruption:** The database exists but is in a bad state.
    - **Catastrophic Data Loss:** The database is deleted or unavailable.
- **Migrations:**
    - **Vector DB Migrations:** Schema changes, engine changes (e.g., LanceDB to Milvus), data residency changes (e.g., US to EU).
    - **KMS Migration:** Customer rotates their encryption key.
    - **MemApp Migrations:** Deprecating AI models or updating the embedding strategy, requiring re-embedding of all data.
- **Synchronization and Data Integrity Bugs:**
    - **MemApp Corruption:** `embedding states` are not created for some data.
    - **Detection Bugs:** Changes in the primary data are not detected and propagated to the vector store.
    - **Task Queue Failures:** The task queue violates its "at least once delivery" guarantee.
- **Operational Risks:**
    - **Runaway Resets:** A bug causing continuous reset loops, leading to spiraling costs and prolonged downtime.

#### 3.2. Constraints

- **Airtable Architecture:** The system is built on top of Airtable's custom, in-memory, single-writer database called "MemApp," which is backed by MySQL. The single-writer, serializable nature of MemApp provides a transaction number that is used for ordering operations and ensuring consistency.
- **Cost:** Memory usage is a significant expense, driving the decision to store embeddings in a separate, more cost-effective system. Generation and storage costs for embeddings must be manageable.
- **Security:** Embeddings are considered sensitive customer data and must be handled accordingly.
- **Third-Party Dependencies:** The system relies on external AI providers (e.g., OpenAI, Bedrock) for embedding generation, which introduces dependencies on their availability, rate limits, and potential model changes.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

[NO INFO]

#### 4.2. Online/business metrics

- **Re-embedding Downtime:** During a "reset" operation (full re-embedding), the p99.9 for the unavailability of semantic search features is under 2 minutes.
- **Reset Monitoring:** The system uses metrics and alerts to monitor for "runaway resets" to control cost and downtime.

#### 4.3. Loss functions

[NO INFO] (The system uses pre-trained models from external providers, so it does not define its own loss function for training.)

### 5. Data (Dataset)

#### 5.1. Data sources

The source data is customer data residing in Airtable's proprietary in-memory database, "MemApp." The specific data to be embedded for a given use case is defined declaratively via a "data subscription" as part of an `embedding config`.

#### 5.2. Labeling strategy

This is an unsupervised problem. The system leverages pre-trained embedding models to capture semantic meaning, so no explicit labels are required.

#### 5.3. Data quality and cleaning

The article mentions "Data Preparation" and "Corpus Choice" as important considerations but does not provide specific details on the cleaning or preparation steps. The embedding strategy includes a "chunking strategy," but details are not provided.

#### 5.4. Data model and state tracking

To manage eventual consistency, the system introduces two key abstractions:
1.  **`embedding config`**: An abstraction in MemApp that maps data to a vector database table. It contains:
    *   `data subscription`: Defines what data to embed.
    *   `embedding strategy`: Defines how to embed the data (e.g., model choice, chunking).
    *   `storage configuration`: Defines where to store the embeddings.
    *   `triggering configuration`: Defines when to re-generate embeddings for out-of-date data.

2.  **`EmbeddingState`**: A state object tracked in MemApp for each piece of data to be embedded. It uses the serializable transaction number from MemApp to order updates and handle out-of-order writes.
    ```
    type EmbeddingState = {
      lastPersistedTransaction: number | null, // Last transaction written to the vector DB
      lastUpdatedTransaction: number          // Last transaction that updated the source data
    }
    ```
    Data is considered "stale" or in need of re-embedding when `lastUpdatedTransaction` > `lastPersistedTransaction`.

### 6. Validation schema

[NO INFO]

### 7. Baseline solution

The baseline is the existing manual workflow where users spend hours searching and analyzing data to find insights. The new system is designed to automate and significantly speed up this process. No technical baseline (e.g., keyword search, BM25) is mentioned.

### 8. Errors and their analysis

The system is designed around a central error handling and migration pattern called "resetting the embedding config." This involves deleting the old config (which triggers cleanup of all associated data in the vector store) and creating a new one, possibly with updated settings. This single pattern is used to handle a wide variety of failures and operational changes.

- **Data/Consistency Errors:** If MemApp data and the vector database are out of sync due to corruption, detection bugs, or task queue failures, a reset can be triggered to rebuild the embeddings from scratch, ensuring consistency.
- **Infrastructure/Migration Errors:** For catastrophic data loss in the vector DB, a reset re-provisions the table and re-generates all embeddings. For migrations (e.g., changing the DB engine, moving from US to EU), the reset process handles the deletion of old data and the creation of new data in the correct location/format.
- **Model/Configuration Errors:** When an AI model is deprecated or the embedding strategy changes, a reset is performed to re-embed all data with the new model/strategy, ensuring that all vectors in a collection are comparable ("apples-to-apples").

A key trade-off of this approach is temporary downtime of the semantic search feature during the reset. This was deemed acceptable given the rarity of resets and the fast re-embedding time (p99.9 < 2 minutes).

### 9. Training pipelines

The system does not involve model training but rather an embedding generation pipeline.

- **Tooling:**
    - **Primary Datastore:** MemApp (custom in-memory DB) and MySQL.
    - **Vector Datastore:** Pluggable architecture; examples mentioned include LanceDB, Milvus, and Opensearch.
    - **Embedding Generation:** A dedicated "embedding service" that makes API calls to external providers like OpenAI and AWS Bedrock.

- **Pipeline Workflow:**
    1.  **Initialization:** A new `embedding config` is created, which provisions a vector database table and generates initial `embedding state` objects for all relevant data chunks.
    2.  **Detection:** When data in MemApp changes, the `lastUpdatedTransaction` in the corresponding `embedding state` is updated transactionally.
    3.  **Triggering:** Tasks are created to generate embeddings for any config with updated data. This occurs within the same transaction as the detection.
    4.  **Generation:** The embedding service processes the tasks, calls the external AI provider's API to get the embedding vectors, and includes retry logic.
    5.  **Persistence:** The generated embeddings are written to the vector database. This write is conditional on the new transaction number being greater than the one already stored for that vector, preventing out-of-order writes.
    6.  **Confirmation:** The service confirms the write with MemApp by updating the `lastPersistedTransaction` in the `embedding state`. This update is also conditional to only ever increase the value.
    7.  **Deletion:** Deleting an `embedding state` or an entire `embedding config` triggers the automatic, conditional deletion of the corresponding data in the vector store.

### 10. Features

The primary features are the embedding vectors themselves, which are numerical representations of customer data.

- **Feature Source:** The raw data is defined by the `data subscription` in the `embedding config`.
- **Feature Generation:** Embeddings are generated by external, pre-trained models from providers like OpenAI.
- **Feature Configuration:** The `embedding strategy` within the `embedding config` allows for configuration of the embedding model and the "chunking strategy."

### 11. Measuring results

#### 11.1. Offline evaluation

[NO INFO]

#### 11.2. A/B testing

[NO INFO]

#### 11.3. Reporting

The success of the system is primarily measured by its operational resilience and ability to handle the numerous failure and migration scenarios described. The key performance metric reported is the **p99.9 re-embedding time of under 2 minutes** during a "reset," which makes the associated downtime acceptable for the product.

### 12. Integration and Serving

#### 12.1. API design

Users interact with the system via "semantic search or direct access." The embedding generation process is asynchronous and eventually consistent.

#### 12.2. Infrastructure

- **Compute:** An "embedding service" handles the generation logic and API calls.
- **Storage:**
    - **Primary Data:** Airtable's custom in-memory database, "MemApp," backed by MySQL.
    - **Vector Data:** A separate, pluggable vector database (e.g., LanceDB, Milvus, Opensearch).
- **AI Models:** External APIs from providers like OpenAI and AWS Bedrock.

#### 12.3. SLAs and fallback strategies

- **SLA:** The system is eventually consistent. During a "reset" operation, the semantic search feature is temporarily unavailable. The downtime is managed to be under 2 minutes at p99.9.
- **Fallback Strategy:** The primary fallback and recovery mechanism for a wide range of system failures is the **"resetting the embedding config"** process. This involves deleting the existing configuration and all its associated data, then re-creating it from scratch. The product layer is designed to handle this temporary unavailability.

### 13. Monitoring

- **Data Quality / Consistency:** The system monitors for inconsistencies between MemApp and the vector store by comparing `lastUpdatedTransaction` and `lastPersistedTransaction` for each embedding. The "reset" mechanism is triggered when the system detects that embeddings are or are about to become invalid.
- **Model Quality / Drift:** The system handles model changes (e.g., deprecation) by triggering a reset to re-embed all data with the new model. This ensures all vectors within a collection remain comparable.
- **Engineering Metrics:** The system uses a combination of metrics, alerts, and rate limiting to prevent "runaway resets," which could cause spiraling costs and extended downtime. Idempotent requests are also used as a safeguard.

### 14. Operations

- **Retraining / Re-embedding Cadence:** Re-embedding is event-driven. It occurs continuously as data changes and is also performed in bulk via the "reset" mechanism in response to operational events.
- **Incident Response:** The "reset" process is the standardized incident response procedure for a vast array of issues, including database corruption, data loss, synchronization bugs, and various migration types.
- **Operational Procedures:** The "reset" mechanism is the core operational primitive for managing the lifecycle of embeddings. It is used for:
    - Disaster recovery (DB corruption/loss).
    - Migrations (schema, engine, data residency, KMS key rotation).
    - Configuration changes (AI provider, model deprecation, embedding strategy).
    - Application-level operations (cloning a base, restoring a snapshot).
- **Safeguards:** To manage the risks of the powerful "reset" mechanism, safeguards are in place, including rate limiting, alerts on reset frequency, and ensuring requests are idempotent.