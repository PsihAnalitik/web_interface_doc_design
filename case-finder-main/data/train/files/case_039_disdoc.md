- Company: Leboncoin
- Title: Once Upon a Chat Bot: The Ada Story at leboncoin
- Technology area: Generative AI & LLM
- Source URL: https://medium.com/leboncoin-tech-blog/once-upon-a-chat-bot-the-ada-story-at-leboncoin-1a4c52000d82
- Content type: article

### 1. Problem definition

#### 1.1. Origin

In the GenAI boom of 2023, Leboncoin's data scientists (DS) and machine learning engineers (MLEs) sought to explore the capabilities of Large Language Models (LLMs). The primary motivation was to create a safe, controlled internal environment for this exploration, driven by concerns over data security with public LLM platforms. A few MLEs initiated the project at the end of 2023 to build an in-house chatbot assistant, named "Ada."

#### 1.2. Relevance & reasons

The project was a direct response to the risks of using public LLMs with sensitive corporate data. High-profile incidents, such as Samsung engineers leaking source code and meeting notes into ChatGPT, highlighted the danger of irreversible data leakage.

Building an internal chatbot was identified as an ideal "playground" for several reasons:
*   **Testing Boundaries**: It provided a hands-on way to discover the strengths and weaknesses of LLMs in a real-world, yet closed, environment.
*   **Upskilling Teams**: It served as a practical, fast-moving, and educational entry point for DS and MLEs new to LLMs.
*   **Security**: It allowed the team to learn quickly without compromising on trust or security, protecting both company data and teams.

As the project evolved, leadership saw Ada as an opportunity to explore the real-world capabilities of GenAI, leading to a push for specialization to serve specific internal knowledge needs.

#### 1.3. Expectations

The initial expectation was to create a "ChatGPT-like experience" for all employees, but with a critical difference: all data and conversations would remain private and secure within Leboncoin's infrastructure.

As adoption grew, expectations evolved:
*   Users began requesting new capabilities.
*   The project's scope expanded from a general-purpose assistant to a collection of domain-specific assistants connected to internal knowledge bases (e.g., Confluence, Lumapps, Backstage).
*   The assistant needed to be more accessible, leading to an integration with Slack.

#### 1.4. Previous work

[NO INFO]

#### 1.5. Usage volumes and patterns

The chatbot was intended for all employees at Leboncoin. Initially, it was a general-purpose assistant accessed via a standalone web interface. Usage patterns shifted towards more specialized queries as domain-specific assistants were developed. To reduce friction, the assistants were later integrated as Slack Apps, bringing the tool into users' existing workflows. Custom Slack features like thread and channel summarization also became popular.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Primary Goal**: Explore LLM capabilities within a safe, controlled infrastructure that protects company data.
*   **Technical Goal**: Build an internal chatbot assistant that provides a private, secure alternative to public LLMs.
*   **Team Goal**: Upskill DS and MLE teams on LLM infrastructure, prompt engineering, RAG pipelines, and security governance.
*   **Product Goal**: Evolve from a generic assistant to a suite of specialized assistants powered by Retrieval-Augmented Generation (RAG) to answer questions about specific internal data sources (Confluence, Lumapps, Backstage, etc.).
*   **Accessibility Goal**: Integrate the assistant into employees' daily workflows, such as Slack.

#### 2.2. Anti-goals

*   **Data Leakage**: The system must not use public GenAI services in a way that risks leaking confidential material.
*   **Data Storage**: The system should not store user conversations to ensure strong privacy.
*   **Data Residency Violation**: The system must not use models or services that process or store data outside of the EU, to comply with legal and privacy requirements (e.g., GDPR).
*   **Long-term Maintenance Burden**: The project was not intended to become a permanent, internally-maintained tool if a secure, cost-effective, and feature-rich enterprise solution became available. The focus was on learning and accelerating GenAI adoption.

### 3. Risks and constraints

*   **Data Security & Privacy**: The primary risk was the potential leakage of sensitive data, including client information, source code, and confidential projects, through public LLM services. This was the foundational concern that initiated the project.
*   **Data Residency**: As a French company, there was a strict legal and security requirement for all data to be processed and stored within the EU. This constrained the choice of cloud providers and models.
*   **Infrastructure Complexity and Cost**: Self-hosting open-source models like Llama 2 proved to be complex, performance-lagged, and more expensive than managed solutions due to the need for large cloud instances.
*   **Organizational Scalability**: The dedicated team (3 MLEs, 2 software engineers) could not keep pace with the company-wide demand for new, custom assistants, which became a key factor in the decision to sunset the project.
*   **Model Performance**: The quality of the underlying LLM was a critical constraint. Self-hosted Llama 2 was found to be inferior in conversational quality and reliability compared to Anthropic's Claude 2.
*   **Tooling Limitations**:
    *   The chosen reranker model (Cohere Rerank 3.5) had a 4,096-token limit, which restricted the size of user queries the system could accept.
    *   A pilot with the open-source platform Onyx revealed stability issues in production due to the complexity of its Vespa database dependency.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The team developed a robust evaluation framework, moving from standard metrics to custom ones that better reflected real-world challenges.
*   **Correctness**: The main metric used for evaluation. It employed an LLM-as-a-judge to evaluate how closely a generated answer matched the ground truth, serving as a reliable indicator of overall system performance.
*   **Correct Links Pulled**: A custom metric that counted whether the correct source links were retrieved and present in the answer. This was found to be a more reliable and precise measure of the retrieval step's performance than LLM-judged metrics like context relevance.
*   **Context Relevance**: An LLM-as-a-judge metric used to evaluate retrieval quality. For the Backstage assistant, this metric was improved from 0.63 to 0.73 by adding a query rephraser.
*   **Answer Relevance**: An LLM-as-a-judge metric comparing the answer to the question. It was found to be unreliable as it failed to detect hallucinations.
*   **Cosine Similarity**: Used initially to compare the LLM-generated response with the expected response, but was ultimately abandoned as it was a poor indicator of quality.

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The system used RAG to connect the chatbot to various internal knowledge bases:
*   **Confluence**: Product and tech documentation.
*   **Lumapps**: Moderation content for the Customer Relations team.
*   **Backstage**: The internal developer portal, containing tech docs, onboarding guides, and API specs.
*   **Organizational Graph**: Data from an OpenSearch index representing the company's organizational structure (teams, squads, crews, leadership).
*   **Static Files**: For a dedicated "Policy assistant".

#### 5.2. Labeling strategy

Evaluation datasets were crucial for iteration and were created on a per-source basis.
*   **Initial Datasets**: Primarily built using question/answer pairs synthetically generated from the source documents.
*   **User-Informed Datasets**: The team later began gathering user feedback to populate the datasets, making them more realistic and reliable.
*   **Targeted Datasets**: Specific datasets were created to diagnose and address known weaknesses. Examples include:
    *   A dataset focused on table-based queries for the Confluence assistant.
    *   Separate datasets for English and French queries for the Backstage assistant to address multilingual challenges.

#### 5.3. Data quality issues and cleaning/enrichment steps

*   **Structural Data Loss**: For Confluence documents, standard chunking methods removed table headers and destroyed the structure of arrays, leading to poor performance on table-related queries.
*   **Multilingual Search Failure**: The Backstage assistant's OpenSearch index was optimized for English (stop-word removal, stemming). This caused poor retrieval performance for queries made in French.
*   **Noisy Keywords**: For the moderation assistant, generic user queries (e.g., "Is an ad about selling a shotgun allowed on the website?") contained noisy keywords like "ad" or "website" that pulled irrelevant document chunks.

### 6. Validation schema

#### 6.1. Train/validation/test split

The project used pre-trained models, so the focus was on evaluating different RAG pipeline configurations rather than model training. Custom evaluation datasets were used for this purpose.

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets and update frequency

*   Dedicated evaluation datasets were maintained for each data source (e.g., a dataset of 120 examples is mentioned).
*   These datasets were updated with real user feedback to improve their reliability.
*   A baseline evaluation was scheduled to run weekly using Airflow to track performance over time.

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

*   **Initial System**: The first version of Ada was a general-purpose chatbot using Anthropic's Claude 2 model via AWS Bedrock, without any RAG capabilities.
*   **Backstage Assistant Baseline**: The simplest approach was to directly use the existing OpenSearch keyword search engine integrated with Backstage. The advanced solution built upon this by adding a query rephraser and a reranker.
*   **RAG Baseline**: For assistants using semantic search, the baseline was a simple retrieval from a vector database. This was then improved with the addition of a reranker and, in some cases, a rephraser.

### 8. Errors and their analysis

#### 8.1. Error taxonomy

*   **Data Preprocessing Errors**:
    *   Chunking of Confluence documents broke table structures, making it impossible to answer questions about tabular data.
*   **Retrieval Errors**:
    *   **Keyword Mismatch**: OpenSearch's English-optimized index failed to retrieve relevant documents for French queries.
    *   **Semantic Ambiguity**: Generic queries for the moderation assistant led to retrieval of irrelevant chunks due to noisy keywords.
    *   **Ranking Failure**: First-pass retrieval methods (cosine similarity, keyword matching) were fast but often failed to place the most relevant content at the top.
    *   **Structural Blindness**: Keyword search on the org chart data could not answer hierarchical questions (e.g., "Which teams belong to this crew?") as it lacked graph awareness.
*   **Model Errors**:
    *   Hallucinations were a concern, and initial metrics like `answer relevance` were not effective at detecting them.
*   **Infrastructure & Deployment Errors**:
    *   Self-hosting Llama 2 led to poor performance and high operational complexity.
    *   A pilot with the Onyx platform suffered from production stability issues related to its Vespa database dependency.

#### 8.2. Diagnostic approaches

*   **Targeted Datasets**: The team built specific evaluation datasets to reproduce and analyze failures, such as for table-based queries and multilingual queries.
*   **Component-Specific Metrics**: The "Correct Links Pulled" metric was created to isolate and precisely measure the performance of the retrieval step.
*   **User Feedback Loop**: User-reported issues were collected, although investigation was complicated by the no-conversation-storage policy.

### 9. Training pipelines

#### 9.1. Tooling

*   **LLMs**: Anthropic Claude 2 and Claude Sonnet (via AWS Bedrock), Cohere Rerank 3.5.
*   **Initial Experiment**: Meta's Llama 2 (self-hosted).
*   **Infrastructure**: AWS, AWS Bedrock.
*   **Data Stores**:
    *   Postgres with a vector extension (for semantic search).
    *   OpenSearch (for lexical search and org chart data).
*   **Evaluation & Experimentation**: Langsmith, Apache Airflow.
*   **Future Tooling (post-Ada)**: n8n (for workflow automation), Custom GPTs, Model Context Protocol (MCP) connectors.

#### 9.2. Preprocessing, training, evaluation, and deployment automation

The project focused on inference pipelines, not model training.
*   **Evaluation Automation**:
    *   Langsmith was used for running batched, reproducible experiments. Its asynchronous evaluation feature reduced the time to evaluate a 120-example dataset from 30 minutes to 3 minutes.
    *   Apache Airflow was used to schedule a weekly baseline evaluation run.
*   **Deployment**: The MVP for the Backstage assistant was deployed in a single sprint. The reranker component was also implemented and evaluated within one sprint.

#### 9.3. Experiment tracking and CI/CD integration

Langsmith was the primary tool for experiment tracking, enabling efficient and reproducible evaluation of different RAG pipeline configurations.

### 10. Features

The "features" of this system are the components of its RAG and query processing pipelines.

#### 10.1. Feature categories and selection criteria

*   **Retrieval Stage**:
    *   **Semantic Retrieval**: Used for unstructured text in Confluence and Lumapps. Documents were chunked, embedded, and stored in a Postgres vectorDB for similarity search.
    *   **Lexical Retrieval**: Used for the Backstage assistant, leveraging its existing OpenSearch index via a "search" API call. This was chosen for its simplicity and reduced infrastructure overhead.
    *   **Full Context Loading**: Used for the Policy and Org Chart assistants, where the entire corpus was small enough to be loaded into the LLM's context window (Claude Sonnet with 200K tokens). This guaranteed complete coverage without a retrieval step.
*   **Reranking Stage**:
    *   **Cross-Encoder Reranker**: Cohere's Rerank 3.5 model was used as a second stage to reorder candidate chunks from the initial retrieval. It was applied to both semantic and lexical retrieval pipelines to improve context quality.
*   **Query Preprocessing Stage (Rephrasers)**:
    *   **Rule-Based Rephraser**: A simple rephraser that stripped generic terms from queries was used for the moderation assistant. It boosted correctness by 10%.
    *   **LLM-Based Rephraser**: A lightweight English keyword rephraser was used for the Backstage assistant to make queries more compatible with the OpenSearch index.
    *   **Auto-Translation Rephraser**: Used in the Backstage assistant to translate queries before search, improving multilingual performance.

#### 10.2. Feature store or batch/offline computation patterns

[NO INFO]

#### 10.3. Feature importance and ablation results

*   **Rerankers**: Adding a reranker provided substantial improvements in answer quality and reliability with minimal latency impact.
*   **Rephrasers**: Their impact was context-dependent.
    *   For the moderation assistant, a simple rule-based rephraser improved correctness by 10%, outperforming a more complex LLM-based rephraser (3-4% improvement).
    *   For the Backstage assistant, a rephraser improved context relevance from 0.63 to 0.73.
    *   For the Confluence assistant, where retrieval already performed well, adding a rephraser hurt performance.

### 11. Measuring results

#### 11.1. Offline evaluation methodology

The team ran frequent and rapid evaluations using Langsmith. This allowed for batched, reproducible experiments to compare different pipeline configurations (e.g., with/without reranker). The core of the evaluation relied on custom datasets and two key metrics: `Correctness` and `Correct Links Pulled`. A weekly baseline evaluation was automated with Airflow to track performance over time.

#### 11.2. A/B test design

The article mentions a pilot with test users for the Onyx platform to evaluate its capabilities in real-world scenarios but does not describe a formal A/B testing framework.

#### 11.3. Reporting format and decision criteria

[NO INFO]

### 12. Integration and Serving

#### 12.1. API design, batch vs. online serving

*   **Serving Mode**: The system operated as an online, interactive chatbot.
*   **Integration Points**:
    *   Initially served through a standalone web interface.
    *   Later integrated as multiple Slack Apps to be closer to user workflows.
    *   Custom Slack features for thread/channel summarization were also developed.
*   **Future Integration**: Post-Ada, the plan was to use Model Context Protocol (MCP) connectors to integrate ChatGPT with internal APIs and build Custom GPTs.

#### 12.2. Infrastructure

*   **Cloud Provider**: AWS.
*   **Model Serving**: AWS Bedrock was used to serve Anthropic's Claude models. An early experiment to self-host Llama 2 on AWS was abandoned.
*   **Databases**:
    *   Postgres with a vector extension for RAG vector storage.
    *   OpenSearch for lexical search and storing organizational data.

#### 12.3. SLAs, latency budgets, and fallback strategies

*   **Privacy SLA**: A key design principle was that no conversations were stored, ensuring user privacy.
*   **Latency**: The addition of a reranker had a "minimal" impact on system latency. No specific latency budgets are mentioned.
*   **Fallback Strategies**: [NO INFO]

#### 12.4. Release cycle for models vs. infrastructure

The team worked in agile sprints. The implementation of the reranker, including evaluation, was completed in a single sprint. The MVP for the Backstage assistant was also deployed in one sprint.

### 13. Monitoring

#### 13.1. Data quality and schema checks

[NO INFO]

#### 13.2. Model quality and prediction drift

A weekly evaluation pipeline was scheduled using Airflow to run against a baseline dataset. This served as a recurring check on the quality and performance of the RAG systems.

#### 13.3. Input/target drift detection methods and thresholds

[NO INFO]

#### 13.4. Engineering metrics

*   **Cost**: The team monitored costs, noting that self-hosting Llama 2 was more expensive than using the managed AWS Bedrock service, even with optimizations like turning off compute during off-hours.
*   **Stability**: System stability was monitored, particularly during the pilot of the Onyx platform, which was found to be unstable in production due to its Vespa database dependency.

#### 13.5. Alerting and tooling

[NO INFO]

### 14. Operations

#### 14.1. Day-to-day operational procedures

[NO INFO]

#### 14.2. Retraining cadence and ownership

*   **Retraining**: Not applicable, as the system used pre-trained, third-party LLMs.
*   **Evaluation Cadence**: A baseline evaluation was run weekly.
*   **Ownership**: A dedicated team was formed, consisting of three MLEs, two software engineers, a Product Owner, and a manager.

#### 14.3. Incident response and rollback procedures

Investigating user-reported issues was noted to be complex and challenging because, for privacy reasons, no conversations were stored.

#### 14.4. Non-engineering considerations

*   **Project Lifecycle**: The Ada project ran for approximately 1.5 years (late 2023 to Q1 2025). It was strategically sunsetted in favor of adopting ChatGPT Enterprise, which had recently launched with EU data residency.
*   **Knowledge Transfer**: The decision was made to transfer Ada's "secret sauce" to the new platform. This involved porting features via MCP connectors, reimagining them as Custom GPTs, and using tools like n8n for automation to avoid heavy engineering infrastructure.
*   **Strategic Pivot**: The project was ultimately considered a "high-velocity learning accelerator." The expertise gained was redirected toward more user-facing use cases, while the internal assistant function was handed over to a commercial enterprise solution.