Here is the structured ML system design document based on the provided source material.

---
- **Company**: Linkedin
- **Title**: Practical text-to-SQL for data analytics
- **Technology area**: Predictive ML
- **Source URL**: https://www.linkedin.com/blog/engineering/ai/practical-text-to-sql-for-data-analytics
- **Content type**: article
---

### 1. Problem definition

#### 1.1. Origin

The system, named **SQL Bot**, is an internal AI-powered assistant developed at LinkedIn to address inefficiencies in data access. Data experts spend a significant amount of time helping colleagues find and query data, creating a bottleneck for both data teams and business partners awaiting insights. SQL Bot is integrated within LinkedIn's internal data science platform, **DARWIN**, and aims to democratize data access by transforming natural language questions into SQL queries.

#### 1.2. Relevance & reasons

The primary motivation is to free up data experts' time from routine data retrieval tasks, allowing them to focus on more complex analysis and strategic initiatives. By enabling employees across various functions to self-serve their data needs, the system reduces delays and empowers business partners to get crucial insights faster. The system is designed to be practical for a complex enterprise environment with a massive data warehouse.

#### 1.3. Expectations

The system is expected to:
- Accept natural language questions from users.
- Identify the correct, authoritative data sources (tables) from a vast and complex data warehouse.
- Generate accurate SQL queries to answer the user's question.
- Automatically detect and fix errors in the generated SQL.
- Respect and handle dataset permissions to prevent access-denied errors.
- Provide a conversational and interactive user experience.

#### 1.4. Previous work

A proof-of-concept prototype was developed as a standalone chatbot application. However, this version saw 5-10x lower adoption compared to the current system, which is deeply integrated into the DARWIN platform, highlighting the importance of meeting users within their existing workflows.

#### 1.5. Usage volumes and patterns

- **Users**: The system is used by "hundreds of employees" across LinkedIn’s diverse business verticals.
- **Data Scale**: The LinkedIn data warehouse contains "millions" of tables. The system must effectively search and filter this vast space.
- **Usage**: A key feature, "Fix with AI," which helps users debug their own failing queries, accounts for 80% of the system's sessions.

### 2. Goals and anti-goals

#### 2.1. Goals

- **Data Democratization**: Enable non-expert users across different functions to independently access data insights via natural language.
- **Accuracy**: Generate semantically and syntactically correct SQL queries that accurately answer the user's question.
- **Context Awareness**: Correctly identify the most relevant tables and fields from millions of options, considering implicit user context (e.g., their team or role).
- **User Experience**: Provide a fast, easy-to-use, and conversational interface integrated into the user's primary workflow (DARWIN).
- **Error Handling**: Proactively validate generated queries and use a self-correction mechanism to fix errors.
- **Customizability**: Allow users and teams to customize the bot's behavior and knowledge for their specific domain without platform team intervention.
- **Multi-Intent Handling**: Respond appropriately to various user needs beyond just query generation, such as finding tables, explaining schemas, or answering general SQL syntax questions.

#### 2.2. Anti-goals

- **Generate SQL for every input**: The system should not assume every user input is a request for a SQL query. It must classify user intent and respond accordingly.
- **Generate overly complex queries**: For simple questions, the system should avoid generating unnecessarily complicated or multi-step queries. The query planner is explicitly instructed to minimize the number of steps.

### 3. Risks and constraints

- **Data Scale and Complexity**: The data warehouse has millions of tables, making table discovery a significant challenge.
- **Metadata Quality**: Table and field descriptions are often absent or incomplete, hindering effective retrieval.
- **Data Volatility**: Tables and fields are frequently added, deprecated, and replaced over time, meaning the "source of truth" for a given question can change.
- **Implicit User Context**: User questions are often ambiguous without implicit context (e.g., "What was the average CTR yesterday?" has different meanings for ads, email, or search teams).
- **Access Control**: Users may not have permission to run queries against the tables identified by the bot, leading to a frustrating user experience. This is a key constraint the system must handle.
- **User Adoption**: A standalone tool is unlikely to be adopted. The system must be integrated into existing, high-traffic developer environments like DARWIN.
- **Dependency**: The system relies on LinkedIn's internal metadata tool, **DataHub**, for schema information and deprecation signals.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

A benchmark set of over 130 questions is used for offline evaluation.
- **Retrieval Quality**:
    - **Table/Field Recall**: Percentage of correct tables/fields from the ground truth that were retrieved. Adding re-rankers, descriptions, and example queries improved table recall.
    - **Table/Field Hallucination Rate**: Percentage of retrieved tables/fields that do not exist.
- **Query Quality**:
    - **Syntax Correctness**: Whether the generated SQL is syntactically valid, often checked using an `EXPLAIN` statement.
- **Performance**:
    - **Response Latency**.
- **Semantic Accuracy (LLM-as-a-judge & Human Eval)**:
    - **Overall Score**: A holistic quality score.
    - **Component Correctness**: Rubric-based evaluation of tables, columns, joins, filters, aggregations, etc.
    - **Query Efficiency/Complexity**: Assessment of the quality of the generated query.

#### 4.2. Online/business metrics

- **Adoption**: Number of active users ("hundreds of employees").
- **Usage**: Session volume, with specific tracking for features like "Fix with AI" (80% of sessions).
- **User Satisfaction**: Measured via surveys. In a recent survey:
    - ~95% rated query accuracy "Passes" or above.
    - ~40% rated query accuracy "Very Good" or "Excellent".

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The system uses a variety of data sources to build context for the LLM, organized into a knowledge graph:
- **Table Metadata**: Sourced from **DataHub**, including table schemas, field descriptions, top K values for categorical fields, partition keys, and field classifications (metrics, dimensions).
- **Dataset Certification Program**: A manual effort where domain experts provide mandatory descriptions for key tables and optional field descriptions.
- **AI-Generated Annotations**: Descriptions are augmented with AI-generated content based on existing documentation and Slack discussions.
- **User-Dataset Access History**: Used to personalize table retrieval. Access popularity helps narrow down tables, and Independent Component Analysis (ICA) on access history helps infer user context.
- **Query Logs**: Used to derive aggregate information like table/field popularity and common table joins.
- **Example Queries**: Sourced from internal wikis and certified **DARWIN** notebooks. Notebooks are filtered using heuristics for recency and reliability (e.g., high execution count).
- **User-Provided Knowledge**:
    - Domain knowledge collected via the SQL Bot UI.
    - Custom instructions provided by users.
    - User-defined dataset collections for specific product areas.
- **Deprecation Signals**: Datasets and fields marked as deprecated in DataHub are used to offboard them from the system.

#### 5.2. Labeling strategy

- A benchmark dataset of over 130 questions was created in collaboration with domain experts from 10 product areas.
- Each question includes one or more ground truth SQL queries.
- Approximately 60% of benchmark questions have multiple accepted answers, as there are often several correct ways to write a query. Not accounting for this underreported recall by 10-15%.
- The ground truth is reviewed and updated every 3 months by human experts, guided by an LLM-as-a-judge process that flags potential new correct answers.

### 6. Validation schema

- **Benchmark-driven Evaluation**: All changes are evaluated against a curated benchmark set of 130+ questions.
- **Ground Truth Management**: The ground truth is a living dataset. It is reviewed every 3 months by experts to add new, valid query answers. This process is aided by an LLM-as-a-judge, which flags queries where its high score disagrees with the existing ground truth. The LLM-as-a-judge score is within 1 point of the human score 75% of the time.
- **Evaluation Methodology**:
    1. **Automated Metrics**: The first phase of development focused on easily computable metrics like table/field recall, hallucination rate, and syntax correctness.
    2. **Semantic Evaluation**: For deeper accuracy assessment, the system uses a combination of human evaluation and LLM-as-a-judge. This is preferred over executing queries and comparing results because it doesn't require data access, can assess partially correct queries, and provides detailed feedback for improvement.

### 7. Baseline solution

The article implies an evolutionary approach rather than a single baseline model.
- **Initial Prototype**: A standalone chatbot application. Its low adoption demonstrated the need for deep workflow integration.
- **Simple Feature**: The "Fix with AI" feature, which debugs a user's existing query, was identified as a high-ROI, easy-to-develop starting point that accounts for 80% of current usage. This suggests a strategy of starting with a narrow but high-value use case.

### 8. Errors and their analysis

- **Error Taxonomy**:
    - **Retrieval Errors**: Failing to find the correct tables or fields due to poor metadata or ambiguous questions.
    - **Generation Errors**:
        - **Syntax Errors**: Invalid SQL syntax.
        - **Semantic Errors**: Correct syntax but wrong logic (e.g., incorrect joins, filters, or aggregations).
        - **Hallucinations**: Using non-existent tables or fields.
        - **Complexity Errors**: Generating overly complex queries for simple requests.
    - **Post-execution Errors**: Query fails upon execution due to permissions issues.

- **Error Mitigation and Analysis**:
    - **Self-Correction Loop**: A dedicated agent is used to fix errors.
        1. **Validators**: A set of validators run on the generated query. They check for table/field existence and execute the `EXPLAIN` statement to catch syntax errors.
        2. **Correction Agent**: Errors from the validators are fed to a self-correction agent. This agent is equipped with tools to retrieve additional context (e.g., more tables/fields) and rewrite the query.
    - **Access Control Handling**: Before presenting the query, the system checks if the user has the necessary permissions via group memberships and automatically provides the code to leverage those credentials, preventing access-denied errors.
    - **User-in-the-loop**: The "Fix with AI" feature allows users to submit their own failing queries for analysis and correction. The guided experience allows users to provide feedback at each step of the generation process.

### 9. Training pipelines

- **Tooling**:
    - **Orchestration**: The multi-agent system is built using **LangChain** and **LangGraph**.
    - **Platform**: The system is hosted and integrated within **DARWIN**, LinkedIn's internal data science platform.
    - **Metadata Store**: **DataHub** is used for schema discovery and metadata management.
    - **Vector Store**: An unnamed vector store is used to index popular tables and example queries for retrieval.
- **Automation and CI/CD**:
    - **Context Ingestion**: The system automatically ingests popular tables from query logs into the vector store.
    - **Context Pruning**: It automatically offboards deprecated datasets and fields using signals from DataHub.
    - **Experimentation**: The system has many hyperparameters (embedding choices, context windows, prompts, agent memory, etc.), which are tuned and evaluated against the benchmark set.

### 10. Features

In this RAG system, "features" are the contextual information retrieved and provided to the LLM at generation time.
- **Retrieval & Ranking Context**:
    - **User Query**: The initial natural language input.
    - **Personalization**:
        - Default datasets inferred from the user's position in the organizational chart.
        - Personalized "components" (sets of datasets) derived from Independent Component Analysis (ICA) on user-dataset access history.
    - **Table Metadata**: Descriptions, popularity metrics.
    - **Example Queries**: Relevant queries from certified notebooks.
    - **Domain Knowledge**: User-provided context and explanations of internal jargon.
- **Query Writing Context**:
    - **Selected Table Schemas**: Full schemas for the top-ranked tables, including field descriptions, top K values, and other attributes.
    - **Field Popularity**: Fields are ordered by access frequency over a recent time window.
- **User-Provided Context**:
    - **Product Area**: Users can select a "product area," which filters for datasets commonly used by that group.
    - **Custom Instructions**: User-supplied text that provides domain knowledge or behavioral guidelines for the bot.

### 11. Measuring results

- **Offline Evaluation**:
    - Performed using the 130+ question benchmark set.
    - The process involves comparing the model's output against ground truth answers using a combination of automated metrics (recall, syntax) and a detailed rubric evaluated by humans and an LLM-as-a-judge.
- **A/B testing**
    [NO INFO]
- **Reporting**:
    - User satisfaction is tracked via surveys.
    - Key usage metrics (e.g., adoption, session volume, feature usage) are monitored to gauge success and identify high-value areas.
    - The benchmark is reviewed every 3 months to ensure it reflects the current state and to incorporate new valid answers discovered during evaluation.

### 12. Integration and Serving

- **Architecture**: A multi-agent system built on **LangChain** and **LangGraph**. The overall flow is a Retrieval-Augmented Generation (RAG) pipeline with multiple stages of ranking, planning, and correction.
- **Serving Flow**:
    1. **Intent Classification**: The user's question is first classified to determine the right response type (e.g., generate SQL, find tables, explain concepts).
    2. **Personalized Filtering**: The search space of millions of tables is narrowed to a few thousand using access popularity and user-specific personalization (org chart, ICA components).
    3. **Retrieval (EBR)**: Embedding-Based Retrieval is used to find the top 20 semantically relevant tables.
    4. **LLM Re-ranking**: An LLM re-ranker selects the top 7 tables from the 20 candidates, using a rich set of context from the knowledge graph. A second LLM re-ranker selects the most relevant fields from those tables.
    5. **Iterative Query Generation**: A query planner breaks down the problem and incrementally builds the final query. The planner is optimized to produce concise queries for simple questions.
    6. **Validation and Self-Correction**: The generated query is passed through validators (`EXPLAIN`, table/field existence checks). Errors are sent to a self-correction agent to be fixed.
    7. **Response Presentation**: The final output is displayed in a rich UI element showing the formatted query, an explanation, and validation check results.
- **Integration**:
    - SQL Bot is integrated directly into the **DARWIN** platform UI.
    - Entry points include a sidebar widget and a "Fix with AI" button that appears when a user's query fails.
- **SLAs and Fallbacks**:
    - "Fast responses" are a stated goal, but no specific latency budget is given.
    - The system is conversational, allowing for follow-up questions and clarification. A "guided experience" mode allows the user to interact and provide feedback at each step (table selection, query plan step), serving as a human-in-the-loop fallback.

### 13. Monitoring

- **Data/Context Drift**:
    - **Staleness**: Deprecated datasets are automatically removed from the retrieval context using signals from DataHub.
    - **Newness**: Popular new tables are automatically ingested into the vector store by monitoring query logs.
- **Model Quality Drift**:
    - **Benchmark Evaluation**: The model's performance is continuously tracked against the benchmark set.
    - **Human-in-the-loop Review**: The benchmark itself is reviewed every 3 months by human experts. Disagreements between the LLM-as-a-judge and the existing ground truth are used to identify potential model drift or new valid answers, which are then reviewed by experts.
- **Business Metrics**:
    - User adoption and satisfaction are monitored through usage tracking and periodic surveys.
- **Engineering Metrics**:
    - Response latency is a key metric evaluated as part of the benchmark.

### 14. Operations

- **Retraining and Context Management**:
    - The knowledge base is updated continuously and automatically (ingesting popular tables, removing deprecated ones).
    - The benchmark set is manually reviewed and updated by experts every 3 months.
- **Self-Serve Customization**: The platform is designed to empower users to improve performance for their own domains without filing tickets. Users have three main levers:
    1. **Dataset Customization**: Define a collection of relevant datasets for a specific "product area."
    2. **Custom Instructions**: Provide free-text instructions in the DARWIN UI to guide the bot's behavior and provide domain knowledge.
    3. **Example Queries**: Add new, high-quality example queries by creating a notebook in DARWIN and tagging it as "certified."
- **User Experience Operations**:
    - Chat history is saved for continuity.
    - An in-product feedback mechanism is available.
    - The UI provides "quick replies" to guide users on possible interactions.
    - Rich display elements are used to present tables and queries with their associated metadata and explanations.