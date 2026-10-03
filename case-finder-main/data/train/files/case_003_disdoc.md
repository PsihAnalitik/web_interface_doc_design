**Company**: Nubank
**Title**: AskNu: A RAG solution to increase Employees Productivity at Nubank
**Technology Area**: RAG
**Source URL**: https://building.nubank.com/ai-solution-for-search/
**Content Type**: article

### 1. Problem definition

#### 1.1. Origin

With a global workforce of approximately 9,000 employees, Nubank's internal knowledge is vast and decentralized. Each team maintains its own processes and documentation on Confluence, which supports team autonomy but complicates information discovery for employees outside a specific team.

The problem is that employees spend a significant amount of time trying to find the right information or figuring out which team is responsible for a specific topic. This friction often leads to the creation of support tickets, consuming both the employee's time and the support team's resources.

#### 1.2. Relevance & reasons

The primary goal is to streamline access to internal information at scale, empowering employees with self-service capabilities. By providing a centralized, intelligent search tool, Nubank aims to:
*   Reduce the time employees spend searching for information.
*   Decrease the volume of internal support tickets.
*   Increase overall employee productivity and agility.
*   Maintain the existing model of team-owned content while improving its accessibility.

#### 1.3. Expectations

The solution, named AskNu, is expected to be an AI-powered tool integrated into Slack for ease of access. Users should be able to ask questions in a friendly, conversational interface and receive timely, personalized answers based on the company's Confluence documentation. In cases where the answer is unsatisfactory, the user should be seamlessly guided to the correct support portal to create a ticket.

#### 1.4. Previous work

The existing workflow for information retrieval is manual and inefficient:
1.  Employees search through numerous Confluence pages.
2.  If the information is not found, they try to identify the responsible team.
3.  Finally, they open a support ticket and wait for a response.

This process can take anywhere from 30 minutes to 8 hours.

#### 1.5. Usage volumes and patterns

The system is designed to serve all 9,000 Nubank employees. Six months after its general release, the system had:
*   **Users**: 5,000 distinct users.
*   **Messages**: 280,000 user messages.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Productivity**: Significantly reduce the time required for employees to find information, from 30 minutes-8 hours down to seconds.
*   **Ticket Reduction**: Achieve a high ticket deflection rate for queries that can be answered by existing documentation.
*   **User Experience**: Provide a fast, accurate, and user-friendly conversational interface on Slack.
*   **Adoption & Retention**: Achieve high adoption among employees and encourage repeat usage.
*   **Scalability**: The system must handle a growing knowledge base and user load.

#### 2.2. Anti-goals

*   **Avoid Cross-Domain Contamination**: The system must not generate answers by mixing documentation from different departments. This is a key architectural driver to prevent inaccurate and confusing responses.
*   **Isolate Internal vs. General Queries**: The system should not use internal, proprietary documentation to answer general knowledge questions (e.g., translations, summarizations). These queries must be routed to an "External Source".

### 3. Risks and constraints

#### 3.1. Risks

*   **Inaccurate Answers**: The LLM could generate factually incorrect or confusing answers, eroding user trust. This is mitigated by the two-stage search architecture and providing source document links.
*   **Outdated Information**: The knowledge base could become stale as teams update their Confluence pages. This is mitigated by frequent re-indexing.
*   **Poor User Experience**: If answers are consistently unsatisfactory, users will revert to opening tickets. This is mitigated by a fallback mechanism that directs users to the correct support portal.
*   **Router Failure**: The initial classification step could route the query to the wrong department, leading to an irrelevant or incorrect answer.

#### 3.2. Constraints

*   **Dynamic Knowledge Base**: The source documentation on Confluence is updated frequently. This makes fine-tuning an LLM for every update prohibitively expensive and impractical.
*   **Content Ownership**: The system must respect the decentralized ownership of documentation by different departments.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Router Quality**:
    *   **Precision**: 78%
    *   **Recall**: 77%
*   **Answer Quality**:
    *   **Accuracy**: 74% of answers for internal domain requests were labeled as accurate during regular audits by department owners.

#### 4.2. Online/business metrics

*   **User Adoption**: 5,000 distinct users in the first 6 months.
*   **User Engagement**: 280,000 user messages processed.
*   **User Satisfaction**: 80% positive feedback (based on a 6% user response rate).
*   **Ticket Deflection**: 96% for internal domains (calculated as the number of tickets avoided by using the tool).
*   **User Retention**: 70% of users return to the tool within a 30-day period.
*   **Latency**: 9 seconds average time to get an answer.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The primary data source is the complete set of departmental documentation pages on Nubank's internal Confluence instance.

#### 5.2. Labeling strategy

*   **For Routing**: Labels are derived from metadata. Each document chunk is associated with its source department, which serves as the class label for the dynamic few-shot classifier.
*   **For Answer Quality**: Department owners regularly audit generated answers and manually label them for accuracy. This feedback is used to identify opportunities for improving the source documentation.

#### 5.3. Available metadata

For each document chunk, the following metadata is extracted and stored:
*   Chunk ID
*   Document Title
*   Document URL
*   Department (owner of the Confluence space)

#### 5.4. Data quality issues

The "Next Steps" section indicates that the team is working on addressing known data quality issues, including:
*   Duplicate documentation.
*   Inconsistent information across documents.
*   Inexistent documentation for frequently asked questions.

#### 5.5. ETL

An automated indexing pipeline runs every 2 hours to keep the knowledge base fresh. The process is as follows:
1.  **Extraction**: Textual information is extracted from every Confluence department page.
2.  **Chunking**: Each document is divided into smaller chunks.
3.  **Metadata Association**: Each chunk is associated with its source metadata (ID, title, URL, department).
4.  **Embedding**: An LLM is used to convert the text of each chunk into a numerical vector embedding representing its semantic meaning.
5.  **Loading**: The embeddings and their corresponding metadata are stored in a knowledge base (vector database).

### 6. Validation schema

[NO INFO]

### 7. Baseline solution

The baseline is the existing manual process for employees. The performance of AskNu is directly compared against this baseline:
*   **AskNu**: 9 seconds to get an answer.
*   **Manual Search**: Up to 30 minutes to find the answer on Confluence.
*   **Support Ticket**: Up to 8 hours to get a response after opening a ticket.

### 8. Errors and their analysis

*   **Router Errors**: The router component, which classifies the user's query into a department, has a precision of 78% and recall of 77%. This indicates that around 22-23% of queries may be initially misrouted, leading to a search in the wrong document set.
*   **Generator Errors**: Even with the correct documents, the final answer can be inaccurate. Manual audits show a 74% accuracy rate for answers on internal topics, meaning 26% of answers are considered inaccurate. These audits are performed by department owners to find opportunities to improve the source documentation.
*   **Data-Induced Errors**: Errors can stem from the source data itself, such as duplicate, inconsistent, or missing documentation. The team plans to build tools for content governance to address this.

### 9. Training pipelines

The system is based on the Retrieval-Augmented Generation (RAG) framework and does not involve traditional model training or fine-tuning. Instead, it relies on an indexing pipeline and in-context learning at inference time.

*   **Indexing Pipeline**:
    *   **Frequency**: Runs automatically every 2 hours.
    *   **Process**: Extracts, chunks, and embeds all Confluence documentation into a vector knowledge base.
    *   **Tooling**: [inferred] The pipeline likely uses standard data processing tools (e.g., Python scripts) and an embedding model service.
*   **Experiment Tracking**: [NO INFO]
*   **CI/CD**: [NO INFO]

### 10. Features

*   **Primary Features**:
    *   **Document Embeddings**: Semantic vector representations of text chunks from Confluence pages. These are pre-computed and stored in the knowledge base.
    *   **Query Embedding**: A semantic vector representation of the user's query, generated in real-time.
*   **Metadata Features**:
    *   **Department**: Used as a filter in the second search stage and as a label for the few-shot classification prompt.
    *   **URL**: Provided to the user as a source reference for transparency and further reading.
    *   **Title**: Retained as part of the chunk's metadata.

### 11. Measuring results

*   **Offline Evaluation**:
    *   The router component was evaluated using Precision and Recall.
    *   Answer quality is evaluated via regular, manual audits by content owners, who label answers for accuracy.
*   **A/B Test Design**: [NO INFO]
*   **Reporting**: The performance of the system is tracked via a set of business and operational metrics (user adoption, engagement, ticket deflection, latency, etc.) which are reported after 6 months of general availability.

### 12. Integration and Serving

The system is integrated as a chatbot application within Slack. The serving architecture is a two-stage RAG process designed to ensure domain separation. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_003/img_011.png`)

1.  **Query Input**: A user sends a message to the AskNu bot on Slack.
2.  **Query Embedding**: The user's query is converted into an embedding.
3.  **Stage 1: Routing Search**: A vector search is performed against the entire knowledge base to retrieve the most relevant document chunks, regardless of department.
4.  **Stage 1: Dynamic Few-Shot Classification (Routing)**:
    *   The retrieved chunks, their corresponding department metadata, and the user query are formatted into a prompt for an LLM.
    *   Examples of general queries (translation, summarization) are also included in the prompt to allow classification to "External Source".
    *   The LLM acts as a few-shot classifier, determining the most appropriate department (e.g., "IT Engineering", "People & Culture") or "External Source" for the query.
5.  **Stage 2: Generation Search**: A second, new vector search is triggered. This search is filtered to only include chunks from the department identified by the router.
6.  **Stage 2: Answer Generation**:
    *   The chunks retrieved from the filtered search and the original user query are passed to an LLM.
    *   The LLM generates a personalized, natural language answer based on the provided context.
7.  **Response to User**: The final answer is sent to the user on Slack, along with the URLs of the source documents used to generate it.

#### 12.1. SLAs

*   **Latency**: The average response time is 9 seconds.

#### 12.2. Fallback strategies

If a user is not satisfied with the generated answer, they are given an option to be redirected to the specific portal of the identified department, where they can create a support ticket.

### 13. Monitoring

*   **Data Quality**: The knowledge base is refreshed every 2 hours to monitor and mitigate data staleness. Future work is planned for monitoring content quality (duplicates, inconsistencies).
*   **Model Quality**:
    *   **Router**: Monitored via offline Precision (78%) and Recall (77%) metrics.
    *   **Generator**: Monitored via regular manual audits of answer accuracy (74%) by department owners.
*   **Business Metrics**: Dashboards track key performance indicators such as user count, message volume, ticket deflection rate (96%), user retention (70%), and user satisfaction (80% positive feedback).
*   **Engineering Metrics**: System latency is monitored, with a current average of 9 seconds per answer.

### 14. Operations

*   **Retraining Cadence**: There is no model retraining. The knowledge base is updated through a re-indexing pipeline that runs every 2 hours.
*   **Ownership**:
    *   The solution is a collaborative effort by the IT Engineering, People & Culture, and NuLLM teams.
    *   Individual department owners are responsible for maintaining their Confluence documentation and for auditing the quality of answers generated from their content.
*   **Incident Response**: For unsatisfactory answers, the primary response is the built-in fallback mechanism that directs the user to the correct portal to open a ticket.
*   **Future Enhancements**:
    *   Continuously improve the router to increase end-to-end metrics.
    *   Integrate with enterprise systems to automate tasks like opening tickets, requesting payslips, or managing access requests directly from the chat interface.
    *   Develop content governance tools to identify duplicate, inconsistent, and missing documentation.