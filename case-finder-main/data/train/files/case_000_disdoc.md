**Company**: Swiggy
**Title**: Hermes: A Text-to-SQL solution at Swiggy
**Technology area**: Generative AI & LLM
**Source URL**: https://bytes.swiggy.com/hermes-a-text-to-sql-solution-at-swiggy-81573fb4fb6e
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

At Swiggy, a data-driven company, many business and product decisions require specific numerical insights from data. Accessing this data is a significant challenge for employees who are not data analysts. The process requires knowledge of SQL, understanding of database schemas, and appropriate data access permissions.

The problem is to enable any team member to ask questions in natural language and receive quantitative answers directly from the company's databases, without needing technical expertise.

#### 1.2. Relevance & reasons

The existing workflow for data retrieval is inefficient and creates bottlenecks:
1.  An employee must hope a relevant dashboard or report already exists.
2.  They must write the SQL query themselves, which requires specialized skills and access.
3.  They must file a request with an analyst, which can take anywhere from a few minutes to several days.

This friction means many important questions may not be asked, or decisions are made with proxy or incorrect information. The "Hermes" system was built to democratize data access, make data more actionable, and compress the time-to-value for insights.

#### 1.3. Expectations

Users expect to ask a question in natural language within Slack and receive both the generated SQL query and the query's results. An example query is: ‘What was the average rating last week in Bangalore for orders delivered 5 mins earlier than promised?’. The system should provide this information instantly.

#### 1.4. Previous work

**Hermes V1**: The initial version was a straightforward implementation using GPT-3.5 variants. Users could provide their own metadata (table and column descriptions) and a prompt to generate SQL.

This "kitchen-sink" approach, which treated all business units and their data uniformly, did not perform well. The complexity of user queries, the large volume of tables and columns, and the need for Swiggy-specific context (e.g., nuances between Food Marketplace and Instamart data) proved to be major challenges. While results were in line with industry benchmarks, they were insufficient for Swiggy's internal needs.

#### 1.5. Usage volumes and patterns

Since its V2 launch, Hermes has been used by hundreds of users across the company to answer several thousand queries over a few months. The average turnaround time for a query is under 2 minutes.

User groups include:
*   **Product Managers and Business Teams**: For sizing initiatives, post-release validation, and checking metrics across dimensions like cities, time slots, and customer segments.
*   **Data Scientists**: For independent deep dives, identifying discrepancies (e.g., predicted vs. actual delivery times), and gathering examples for root cause analyses (RCAs).
*   **Analysts**: For answering specific questions during an analysis and streamlining their validation process (e.g., tracking trends).

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Improved Data Accessibility**: Enable non-technical users to access and analyze Swiggy’s data effectively, reducing dependency on analysts.
*   **Enhanced Decision-Making Speed**: Empower users to make data-driven decisions by quickly extracting insights.
*   **Increased Efficiency and Productivity**: Streamline the data querying process, saving time and effort.
*   **Democratize Data Access**: Make data accessible across the entire organization.

#### 2.2. Anti-goals

*   **Avoid a Monolithic System**: The V1 experience showed that a "kitchen-sink" approach of treating all business needs and data as the same is ineffective. The system should not be a single model for the entire company. Instead, it is compartmentalized for each business unit ("charter").

### 3. Risks and constraints

*   **Ambiguous User Input**: Unclear or ambiguous user prompts can lead to incorrect or partially correct answers from the model.
*   **Data Complexity**: The system must handle a sheer volume of tables and columns, along with complex user queries.
*   **Contextual Nuance**: The system must correctly interpret Swiggy-specific context and terminology, which can differ between business units (e.g., Food vs. Instamart).
*   **Metadata Quality**: The performance of the system is heavily dependent on the quality and completeness of the metadata provided for each business charter.
*   **Data Security**: The system must enforce data access controls, ensuring users can only query tables they are authorized to see. This is a critical constraint.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Query Execution Validation**: Generated SQL queries are validated by running them on the database.
*   **Analyst QA**: For newly onboarded "charters," an automated process generates queries for all defined metrics, which are then sent to a relevant analyst for a "quick QA" to validate the responses.

#### 4.2. Online/business metrics

*   **First-Shot Acceptance Rate**: A user-facing metric collected via a feedback mechanism in Slack. This metric increased dramatically as the system improved and users became more familiar with it.
*   **Average Turnaround Time**: The time from a user submitting a prompt to receiving the result. The target is `< 2 minutes`.
*   **Adoption and Usage**: The number of active users ("hundreds") and total queries processed ("several thousand") are tracked to measure overall impact.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The primary data source is Swiggy's internal data warehouse, which is [inferred] Snowflake. Data is logically partitioned into "charters," which represent distinct business units or logical groups (e.g., Swiggy Food, Swiggy Instamart, Swiggy Genie). Swiggy's in-house data catalog, "Lumos" (based on Alation), is also used.

#### 5.2. Labeling strategy

The system uses a RAG approach, relying on a "Knowledge Base" for context rather than traditional labeled data. This knowledge base is curated for each charter and contains:
*   **Metadata**: Table names, column names, and their descriptions.
*   **Metric Definitions**: Business logic for key metrics.
*   **Reference SQL Queries**: A corpus of ground-truth, verified SQL queries for key metrics.
*   **Historical SQL Queries**: [Planned] A large corpus of historical queries run by users to be used as few-shot examples.

#### 5.3. Data quality issues and cleaning

The importance of high-quality metadata is a key learning. The V2 system's performance is significantly better for charters with well-defined metadata. An automated onboarding process with analyst QA is in place to ensure metadata quality for new charters.

#### 5.4. ETL

An automated process exists for onboarding metadata for new charters. A cron job ensures that queries for all metrics are generated and sent for QA by an analyst. This functions as a metadata ingestion and validation pipeline.

### 6. Validation schema

#### 6.1. Train/validation/test split

The system is not trained from scratch, so traditional splits do not apply. Validation is performed through a combination of automated checks and human-in-the-loop processes.

#### 6.2. Validation approach

1.  **Automated Execution Check**: The generated SQL query is validated by attempting to execute it against the database. If it fails, the error is fed back to the LLM for correction.
2.  **Human-in-the-Loop (Analyst QA)**: When a new charter is onboarded, all its defined metrics are used to generate sample queries. These queries and their results are validated by a subject-matter expert analyst.
3.  **User Feedback**: A feedback mechanism in Slack allows end-users to report the accuracy of the returned query, which is used to identify and fix model misses.

#### 6.3. Holdout sets

The collection of "ground-truth / verified/ reference queries" for key metrics serves as a holdout set to aid the generation process (as few-shot examples) and potentially for evaluation.

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

The baseline was **Hermes V1**, the initial version of the system.

*   **Architecture**: A simple pipeline using GPT-3.5 variants. Users provided their own metadata (table/column descriptions) for a "kitchen-sink" model that served the entire organization.
*   **Performance**: While performance was comparable to industry benchmarks, it was insufficient for Swiggy's complex and context-specific needs.
*   **Limitations**:
    *   Failed to handle the complexity of user queries and the large volume of data.
    *   Could not differentiate context between different business units.
    *   The "kitchen-sink" approach was not scalable or accurate enough.

### 8. Errors and their analysis

*   **Error Taxonomy**:
    *   **User Input Error**: Ambiguous prompts from users lead to incorrect or partially correct SQL generation.
    *   **Metadata Error**: Poor performance is directly correlated with charters that have ill-defined metadata or a high number of tables.
    *   **SQL Generation Error**: The LLM may generate syntactically incorrect SQL. The system attempts to self-correct via a retry loop. If all retries fail, the erroneous query is returned to the user with modification notes.
*   **Error Analysis**: A feedback mechanism is built into the Slack bot, allowing users to report inaccurate queries. This feedback is used to perform Root Cause Analysis (RCA) on model misses and implement fixes.

### 9. Training pipelines

The system uses a RAG-based inference pipeline, not a model training pipeline.

*   **Tooling**:
    *   **User Interface**: Slack
    *   **Middleware**: AWS Lambda
    *   **Compute**: Databricks Jobs
    *   **GenAI Model**: GPT-4o
    *   **Data Warehouse**: Snowflake [inferred]
    *   **Data Catalog**: Lumos (in-house, based on Alation)
*   **Pipeline Architecture (Hermes V2)**:
    1.  **User Prompt**: A user asks a question in a Slack channel.
    2.  **Middleware Trigger**: An AWS Lambda function receives the prompt, performs initial processing, and creates a new Databricks job.
    3.  **Charter Identification**: The job identifies the relevant business "charter".
    4.  **Metrics Retrieval**: Retrieves relevant metrics, associated queries, and historical SQL examples from the charter's Knowledge Base using embedding-based vector lookup.
    5.  **Table and Column Retrieval**: Identifies necessary tables and columns using a combination of LLM querying, filtering on metadata descriptions, and vector-based lookup. For tables with many columns, multiple LLM calls are made to stay within token limits.
    6.  **Few-shot SQL Retrieval**: A vector-based search retrieves relevant ground-truth/reference queries to use as few-shot examples.
    7.  **Structured Prompt Creation**: All gathered information (metrics, tables, columns, few-shot examples, and data snapshots) is compiled into a structured prompt.
    8.  **SQL Generation**: The prompt is sent to the GPT-4o model to generate the final SQL query.
    9.  **Query Validation and Execution**: The generated SQL is run against the database. If it fails, the error is sent back to the LLM for correction (with a set number of retries). Once valid, the query is executed.
    10. **Response to User**: The final SQL query and its results are sent back to the user in Slack.

### 10. Features

The "features" for this RAG system are the components of the structured prompt sent to the LLM.

*   **User Prompt**: The original natural language question.
*   **Charter-Specific Metadata**:
    *   Table names and descriptions.
    *   Column names and descriptions.
    *   Metric definitions.
*   **Retrieved Context**:
    *   **Relevant Metrics**: Identified from the Knowledge Base via vector search.
    *   **Relevant Tables and Columns**: Identified via a multi-step process involving LLMs and vector search.
    *   **Few-shot Examples**: Verified reference SQL queries retrieved via vector search.
    *   **Data Snapshots**: The prompt includes "data snapshots" collected from the database, which could be schema information or sample data rows [uncertain].

### 11. Measuring results

#### 11.1. Offline evaluation

*   Performance is benchmarked against existing solutions from multiple vendors and research papers.
*   A QA process involving analysts is used to validate the outputs for newly onboarded charters.

#### 11.2. A/B testing

[NO INFO]

#### 11.3. Reporting

*   User feedback on query accuracy is collected directly within the Slack bot.
*   Key performance indicators like "first-shot acceptance rate" and usage statistics (user count, query volume) are tracked to measure success and guide improvements.

### 12. Integration and Serving

#### 12.1. API design

The system is exposed to end-users via a Slack bot. The interaction is asynchronous, where a user's prompt triggers a backend job, and the results are posted back to Slack upon completion.

#### 12.2. Infrastructure

*   **Frontend/UI**: Slack
*   **Middleware/Orchestration**: AWS Lambda
*   **Backend Compute**: Databricks Jobs
*   **LLM Provider**: OpenAI (for GPT-4o)
*   **Data Warehouse**: Snowflake
*   **Data Catalog**: Lumos (in-house)

#### 12.3. SLAs and fallback strategies

*   **SLA**: The average turnaround time for a query is under 2 minutes.
*   **Fallback**: If the system cannot generate an executable SQL query after a set number of retries, the last generated (but failed) query is shared with the user along with "modification notes" to guide manual correction.

#### 12.4. Release cycle

The modular design based on "charters" allows for a streamlined product lifecycle, enabling the team to onboard new charters, test outputs, and make continuous adjustments to the Knowledge Base independently for each business unit.

### 13. Monitoring

*   **Data Quality Monitoring**: The system's performance is heavily tied to the quality of the metadata in the Knowledge Base. The onboarding process includes a QA step by analysts to ensure metadata quality.
*   **Model Quality Monitoring**:
    *   A direct user feedback mechanism in Slack is used to collect data on query accuracy.
    *   This feedback is used for RCA on model misses.
    *   The "first-shot acceptance rate" is a key metric for monitoring model performance from a user perspective.
*   **Engineering Metrics**: Average query turnaround time is monitored to ensure it stays below the 2-minute target.
*   **Alerting and Tooling**: [NO INFO]

### 14. Operations

#### 14.1. Retraining cadence

As a RAG system, there is no model "retraining." Instead, the Knowledge Base is continuously updated. The team makes "continuous adjustments to the knowledge base as needed." A planned improvement is to augment the knowledge base with a large corpus of historical queries.

#### 14.2. Onboarding and ownership

A standardized process exists for onboarding new "charters":
1.  The charter's metadata (metrics, tables, columns) is populated in the Knowledge Base.
2.  A cron job automatically generates queries for all defined metrics.
3.  A relevant analyst performs a "quick QA" to validate the generated queries and results.

This modular approach streamlines product lifecycle management and implies distributed ownership of metadata quality at the charter level.

#### 14.3. Incident response and rollback

*   **Query Generation Failure**: The system has a built-in retry mechanism with the LLM. If retries are exhausted, it provides the user with the last failed query and guidance for manual correction.
*   **Data Security**: The system integrates with Snowflake authentication to ensure queries only run on tables the user has access to, preventing unauthorized data access.