**Company**: Digits
**Title**: Assisting Accountants with Similarity-based Machine Learning
**Technology Area**: NLP
**Source URL**: https://digits.com/developer/posts/assisting-accountants-with-similarity-based-machine-learning/
**Content Type**: article

### 1. Problem definition

#### 1.1. Origin

The system, named "Boost," is designed to assist accountants by automating parts of their workflow. The core task is to analyze banking transactions within a client's ledger to spot inconsistencies and suggest appropriate accounting categories for uncategorized transactions. Every second, the Digits platform sifts through transactions to perform this analysis.

#### 1.2. Relevance & reasons

The primary business goal is to save accountants time and prevent embarrassing errors in their clients' books. The problem of transaction categorization is complex and cannot be solved with simple statistical methods. For example, traditional string similarity metrics like Levenshtein distance would fail to identify that a transaction for "STARBUCKS 7663826876" and one for "UBER TRIP 65653625" might both belong to a "Travel" category, as their descriptions are textually dissimilar.

A key challenge is the inherent subjectivity in accounting. Two different accountants might validly classify the exact same transaction into different categories based on client-specific context. For instance, a Starbucks purchase could be categorized as "Meals & Entertainment Expenses" by one accountant, or "Travel" by another if the expense occurred during a business trip. This subjectivity makes a standard single-label classification approach unsuitable. The system is therefore designed as a "co-pilot" to assist human experts, not an "auto-pilot" to replace them.

#### 1.3. Expectations

The system is expected to:
*   Instantly spot inconsistencies in client ledgers, such as transactions in unexpected categories.
*   Suggest categories for new or uncategorized transactions.
*   Handle the subjective nature of accounting by providing recommendations based on historical context rather than a single, absolute prediction.

#### 1.4. Previous work

The use of traditional statistical methods, specifically Levenshtein distance on transaction descriptions, was considered and dismissed. This approach was deemed insufficient because it cannot capture the semantic relationships between transactions that are textually different but contextually similar.

#### 1.5. Usage volumes and patterns

The system operates at a significant scale:
*   **Streaming:** New transactions are analyzed in near real-time ("every second").
*   **Batch:** Batch pipelines process millions of transactions daily.
*   **Vector Index Size:** The vector index used for similarity search contains at least 2 million embeddings.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Assist Experts:** Serve as a "co-pilot" for accountants, speeding up their workflows and providing recommendations.
*   **Automate Tedious Work:** Automate the detection of errors and the suggestion of categories for transactions.
*   **Handle Subjectivity:** Use a similarity-based approach to find historically similar transactions, respecting the fact that multiple categorizations can be valid depending on context.
*   **Scalability:** The system must handle millions of transactions daily in both streaming and batch modes.

#### 2.2. Anti-goals

*   **Full Automation (Auto-Pilot):** The system is explicitly not designed to replace human accountants. It aims to assist, not decide.
*   **Single-Label Classification:** The system avoids predicting a single, definitive category for each transaction. Instead, it surfaces similar past examples to inform the accountant's decision.

### 3. Risks and constraints

*   **Data Subjectivity:** The primary constraint is that transaction categorization is subjective and context-dependent. A model trained for single-label classification would perform poorly.
*   **Scalability of Search:** Brute-force similarity search across millions of transaction vectors is computationally prohibitive. This necessitates an approximation-based approach.
*   **Accuracy vs. Latency Trade-off:** Using Approximate Nearest Neighbor (ANN) search introduces a trade-off. While it dramatically reduces search latency, it comes with a potential reduction in recall (accuracy) compared to an exact, brute-force search.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **ANN Recall:** The recall of the ANN search is measured against the results of a brute-force search. In an evaluation with a 2-million-embedding index, the ANN approach achieved a recall of 0.97.
*   **ANN Latency:** The time taken to find nearest neighbors. In the same evaluation, switching from brute-force to ANN reduced lookup latency by approximately 98%. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_037/img_011.webp`)
*   **Distance Metric:** Cosine distance is used to compare embedding vectors. It is chosen for its effectiveness in high-dimensional spaces, where the angle between vectors is more meaningful than their magnitude.

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

The model is trained using a similarity-based learning approach, conceptually similar to triplet loss. In each training pass, the model is fed an "anchor" transaction, a "positive" sample (a similar transaction), and a "negative" sample (a dissimilar transaction). The model learns to encode these transactions into a vector space such that the anchor is closer to the positive sample and farther from the negative sample.

The definition of "close" (positive) and "far" (negative) is based on training objectives such as:
*   Transactions sharing the same existing category.
*   Associations between different vendors across transactions.

While custom loss functions were initially implemented in TensorFlow, the `TensorFlow Similarity` library is recommended as it provides implementations for these concepts.

### 5. Data (Dataset)

#### 5.1. Data sources

The primary data source is historical banking transactions from the ledgers of Digits' clients.

#### 5.2. Labeling strategy

The system uses existing data as implicit labels for similarity training. No manual labeling is performed. For the triplet training objective, positive and negative pairs are defined by existing metadata:
*   **Positive pairs:** Transactions that fall within the same accounting category.
*   **Negative pairs:** Transactions from unrelated categories.

#### 5.3. Available metadata

The model uses transaction data to generate embeddings. While specific fields are not enumerated, the transaction description is a key input. The model learns to place transactions from similar vendors (e.g., Lyft and Uber) or with similar purposes (e.g., Uber Eats and burger restaurants) close together in the embedding space. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_037/img_006.webp`)

#### 5.4. Data quality issues and cleaning/enrichment

[NO INFO]

#### 5.5. ETL

The system employs both batch and streaming data pipelines to process transactions.
*   **Streaming Pipeline:** When a new transaction arrives, it is picked up within seconds, an embedding is generated, and a similarity search is performed.
*   **Batch Pipeline:** Batch jobs process millions of transactions daily, leveraging the same embedding and search infrastructure.

### 6. Validation schema

#### 6.1. Train/validation/test split strategy

[NO INFO]

#### 6.2. Cross-validation approach

[NO INFO]

#### 6.3. Holdout sets and update frequency

A test set of 128 data points was used to evaluate the performance (latency) and quality (recall) of the ANN search component against a brute-force baseline on an index of 2 million embeddings.

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

The baseline considered was using traditional statistical methods, specifically **Levenshtein distance** on transaction descriptions. This was rejected because it is a purely syntactic measure and fails to capture the semantic similarity required for this task. For example, it would not recognize the relationship between a "Starbucks" transaction and an "Uber" transaction, even if both were related to business travel.

### 8. Errors and their analysis

The primary error analyzed is the trade-off introduced by using Approximate Nearest Neighbors (ANN) search instead of a brute-force method. In an evaluation, the recall of the ANN search dropped slightly to **0.97** compared to the exact results from the brute-force search. This slight decrease in accuracy was deemed an acceptable trade-off for the **98% reduction in lookup latency**.

### 9. Training pipelines

#### 9.1. Tooling

*   **ML Frameworks:** TensorFlow, TensorFlow Extended (TFX).
*   **Similarity Library:** `TensorFlow Similarity` is recommended for implementing similarity-based learning concepts.
*   **Data Processing:** Google Cloud Dataflow is used for batch processing pipelines.
*   **Cloud Platform:** The system is built on Google Cloud Platform.

#### 9.2. Preprocessing, training, evaluation, and deployment automation

The training process involves training a similarity-based model to learn an encoder. The model architecture consists of an input layer, hidden layers, and a dense layer. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_037/img_009.webp`). After training is complete, only the **Encoder** portion of the model is exported and deployed to production endpoints. This encoder is responsible for converting new transactions into their vector embeddings.

#### 9.3. Experiment tracking and CI/CD integration

[NO INFO]

### 10. Features

#### 10.1. Feature categories and selection criteria

The primary input feature is the raw banking transaction. The system learns to generate a single, powerful feature: a **content-aware embedding vector** of a fixed dimensionality that represents the semantic meaning of the transaction.

#### 10.2. Feature store or batch/offline computation patterns

The generated embedding vectors are stored and indexed in a vector database to enable fast similarity search. The chosen tool is **Google Cloud's Vertex AI Matching Engine**, which functions as a managed feature store for embeddings.

#### 10.3. Feature importance and ablation results

[NO INFO]

### 11. Measuring results

#### 11.1. Offline evaluation methodology

The performance of the vector search component was evaluated by:
1.  Generating a vector index with 2 million embeddings.
2.  Querying the index with 128 test data points.
3.  Comparing the latency and recall of the ANN method against a brute-force baseline.
4.  Results showed a **98% latency decrease** with the ANN method at a **recall of 0.97**.

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting format and decision criteria

[NO INFO]

### 12. Integration and Serving

The end-to-end system consists of three stages:
1.  **Generate Embedding:** A transaction is converted into a vector embedding by a deployed encoder model.
2.  **Search Vector Space:** The system searches for related historical transactions using an ANN index.
3.  **Derive Information:** The retrieved similar transactions are post-processed to extract relevant information, such as category suggestions.

#### 12.1. API design, batch vs. online serving

The system supports both serving patterns:
*   **Online/Streaming:** A streaming pipeline processes new transactions "within seconds" of their arrival. This involves real-time embedding generation and lookup.
*   **Batch:** A batch pipeline processes "millions of transactions daily," using Google Cloud Dataflow to orchestrate the consumption of the vector search endpoint.

#### 12.2. Infrastructure

*   **Embedding Model Serving:** The trained encoder model is deployed to "production machine learning endpoints."
*   **Vector Search:** **Google Cloud's Vertex AI Matching Engine** is used as the managed vector database. It is based on the ScaNN library, which uses a Hierarchical Navigable Small World (HNSW) algorithm.
*   **Benefits of HNSW:** This algorithm was chosen over inverse index methods (like LSH) because it allows vectors to be added, updated, and removed from the index at runtime, providing significant operational flexibility.
*   **Managed Service Benefits:** The managed service provides automated sharding for large indexes and autoscaling to handle variable throughput.

#### 12.3. SLAs, latency budgets, and fallback strategies

*   **Latency:** The streaming pipeline is designed to provide suggestions "within seconds." The ANN search component has a significantly lower latency (98% reduction) compared to a brute-force approach.
*   **Fallback Strategies:** [NO INFO]

#### 12.4. Release cycle for models vs. infrastructure

[NO INFO]

### 13. Monitoring

*   **Data quality and schema checks:** [NO INFO]
*   **Model quality and prediction drift:** [NO INFO]
*   **Input/target drift detection:** [NO INFO]
*   **Engineering metrics:** The use of Google Cloud's Vertex AI Matching Engine implies monitoring of service throughput, as it supports autoscaling based on load.
*   **Alerting and tooling:** [NO INFO]

### 14. Operations

#### 14.1. Day-to-day operational procedures

A key operational benefit comes from the choice of the HNSW algorithm for ANN search. Unlike static index approaches, HNSW allows for adding, updating, and removing vectors from the index during runtime. This simplifies keeping the index of historical transactions up-to-date without requiring frequent, costly rebuilds of the entire index.

#### 14.2. Retraining cadence and ownership

[NO INFO]

#### 14.3. Incident response and rollback procedures

[NO INFO]