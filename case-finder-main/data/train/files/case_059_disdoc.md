**Company**: Vimeo
**Title**: From idea to reality: Elevating our customer support through generative AI
**Technology area**: Generative AI & LLM
**Source URL**: https://medium.com/vimeo-engineering-blog/from-idea-to-reality-elevating-our-customer-support-through-generative-ai-101a2c5ea680
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

This project was a prototype initiative at Vimeo to test and demonstrate the capabilities of generative AI. The specific application chosen was a help desk chat prototype that uses AI combined with Vimeo's existing Help Center articles to provide answers to customer questions. The primary scope was the exploration of AI technology, not a complete overhaul of the customer support system.

#### 1.2. Relevance & reasons

Traditional customer support channels at Vimeo often struggle with high query volumes, response delays, and a lack of personalized solutions, which can lead to customer dissatisfaction and churn. The existing systems were identified as having efficiency gaps.

The existing flow for a customer with a question includes:
1.  Opening a ticket with the Vimeo support team.
2.  Searching for a related article in the Vimeo Help Center.
3.  Interacting with a third-party bot that uses intent matching to provide guided workflows or parsed answers.

These methods can be ineffective. For example, a user searching for "domain restrict embed" in the existing Help Center or chatbot does not receive relevant information at a glance and may be directed to submit a support ticket, creating a poor user experience. The prototype aims to provide a more responsive and effective support system.

#### 1.3. Expectations

The prototype is expected to deliver a customer support experience where users can input questions and receive immediate, accurate, and helpful responses. The goal is to improve upon the existing support options by being more efficient and personalized.

#### 1.4. Previous work

The baseline systems that this prototype aims to improve upon are:
*   A manual support ticket system.
*   A keyword-based search engine for the Vimeo Help Center.
*   A third-party chatbot that identifies user intent to guide them through workflows or provide pre-defined answers.

#### 1.5. Usage volumes and patterns

The prototype was developed using a dataset of less than a thousand articles from the Vimeo Help Center. As a proof of concept, production usage volumes like QPS or daily active users are not specified.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Primary Goal**: To test and demonstrate the power of generative AI using a real-world use case and a publicly available dataset (Vimeo's Help Center).
*   **Prototype Goal**: To develop a chat system that provides efficient, useful, and personalized answers to customer support questions.
*   **User Experience Goal**: To provide immediate, accurate, and helpful responses, thereby enhancing customer satisfaction and retention.

#### 2.2. Anti-goals

*   The project's primary focus was **not** to revolutionize Vimeo's customer support system but to serve as a proof of concept for AI applications.
*   The system should **not** answer questions unrelated to Vimeo and its features.
*   The system must **not** answer dangerous or inappropriate questions (e.g., "What's the recipe for dynamite?"). It should instead provide a refusal message.

### 3. Risks and constraints

*   **Response Quality Variability**: LLM outputs can vary significantly, making quality assurance difficult. It is challenging for a QA team to verify the correctness of responses across an unlimited number of possible questions.
*   **Outdated LLM Knowledge**: The underlying LLM's training data may contain outdated information. For instance, ChatGPT was found to have an old copy of Vimeo's Help Center from late 2021 in its training data, causing it to generate outdated or nonexistent links.
*   **Third-Party API Performance**: The performance of external LLM APIs can be inconsistent. During periods of heavy usage, OpenAI's API response speeds were observed to "slow to a crawl."
*   **Data Security**: Using third-party vector stores could create security risks for sensitive information. This was mitigated in the prototype by using a local, on-disk vector store (HNSWLib), which is particularly important for potential future use cases involving internal documentation.
*   **Data Constraint**: The prototype was built using only the publicly available articles from the Vimeo Help Center.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The project involved a qualitative comparison of four different LLM setups: Google Vertex AI Chat Bison, OpenAI ChatGPT 3.5 Turbo, OpenAI ChatGPT 4, and Azure OpenAI ChatGPT 3.5 Turbo. The evaluation was based on the following criteria:

*   **Conciseness**: Google's Bison model produced more concise, bullet-pointed answers compared to the longer, paragraph-style responses from OpenAI's models.
*   **Prompt Adherence**: The Bison model was judged to follow the instruction prompt better than the ChatGPT models.
*   **Response Speed**:
    *   Bison was faster due to generating fewer characters. It returns the entire answer at once.
    *   ChatGPT models support streaming, giving the user immediate feedback, but overall response time can be slow under heavy load.
    *   ChatGPT 4's response speed was "dramatically reduced" compared to ChatGPT 3.5 Turbo.
*   **Response Quality**: ChatGPT 4 was found to deliver "stronger and more concise answers" than ChatGPT 3.5 Turbo.
*   **Cost**:
    *   Google Vertex AI Chat Bison: $0.0005 per 1,000 characters (input and output).
    *   OpenAI ChatGPT 3.5 Turbo: $0.0015 per 1,000 tokens (input) and $0.002 per 1,000 tokens (output).
    *   The article notes that while the pricing models differ (characters vs. tokens), the final costs are "generally close."
    *   ChatGPT 4's price per token is "more than doubled" compared to ChatGPT 3.5 Turbo.

The final model chosen for the prototype was **Google Vertex AI Chat Bison**.

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The primary data source is the content from the Vimeo Help Center, which is powered by Zendesk. All articles are publicly available.

#### 5.2. Labeling strategy

The system uses a Retrieval-Augmented Generation (RAG) approach, which does not require explicit data labeling. The content of the help articles serves as the knowledge base.

#### 5.3. Available metadata

Data is scraped using the Zendesk Help Center API, which provides the following metadata for each article:
*   `body`: The HTML content of the article.
*   `title`: The article title.
*   `html_url`: The full public URL of the article.
*   `label_names`: Tags associated with the article (e.g., "faq", "trademark").
*   `last_modified`: Timestamp of the last modification.

#### 5.4. Data quality issues and cleaning/enrichment

The raw HTML content from the articles is processed by splitting it into smaller chunks. This chunking is done using HTML tags as delimiters, which allows the retrieval system to find specific sections of a relevant article rather than returning the entire document.

#### 5.5. ETL or feature store architecture

The data ingestion pipeline is as follows:
1.  **Scraping**: All published articles are scraped from Vimeo's Zendesk instance via the Zendesk API.
2.  **Intermediate Storage**: Articles are saved into an intermediate JSON file format. This is done to facilitate debugging and allow for ingestion from other sources (e.g., GitHub, Confluence) in the future.
3.  **Chunking**: The JSON files are loaded, and the `body` content is split into smaller chunks based on HTML tags.
4.  **Embedding**: The text chunks are converted into vector embeddings using an AI provider's API (e.g., OpenAI's embedding API).
5.  **Indexing**: The embeddings and their corresponding metadata are indexed into a vector store. For the prototype, HNSWLib running on a local disk was used.
6.  **Continuous Updates**: A webhook from Zendesk is configured to trigger updates to the vector store, allowing for near real-time adding, removing, or replacing of articles as they are modified in the Help Center.

### 6. Validation schema

#### 6.1. Train/validation/test split strategy

A traditional train/test split is not applicable. Validation was performed through a qualitative, comparative analysis of different LLM providers and models on a set of test queries.

#### 6.2. Cross-validation approach

[NO INFO]

#### 6.3. Holdout sets

[NO INFO]

#### 6.4. Leakage risks and how they are mitigated

A form of data leakage was identified: the base LLM (ChatGPT) was pre-trained on an old version of the Vimeo Help Center (from late 2021). This caused the model to sometimes generate outdated or incorrect information (e.g., broken links) from its internal knowledge. The RAG architecture mitigates this by providing up-to-date, relevant context from the vector store with every prompt. To prevent the model from hallucinating source links, the system explicitly uses the `html_url` from the retrieved document's metadata to display sources, rather than asking the LLM to generate them.

### 7. Baseline solution

The existing customer support options serve as the baseline for comparison:
1.  **Manual Support Tickets**: Users can open a ticket with the support team.
2.  **Help Center Search**: A standard search bar for the knowledge base.
3.  **Third-Party Chatbot**: A bot that uses intent recognition to provide guided workflows or simple, parsed answers.

The article demonstrates that this baseline is insufficient, citing an example where a query for "domain restrict embed" fails to provide a useful answer.

### 8. Errors and their analysis

*   **Model Hallucination**: The LLM was found to generate outdated or nonexistent URLs based on its old training data.
    *   **Mitigation**: The system was designed to provide source links directly from the metadata of the retrieved documents, not from the LLM's generated text.
*   **Inconsistent Response Quality**: LLM responses can be highly variable.
    *   **Mitigation**: The `temperature` parameter in the LLM API call is set to `0` to reduce randomness and make responses more deterministic and consistent for the same question.
*   **Out-of-Scope Questions**: The system could be used to ask questions unrelated to Vimeo or even dangerous questions.
    *   **Mitigation**: A detailed instruction prompt is included in the request to the LLM, directing it to refuse to answer any questions not related to Vimeo. For such questions, it generates a canned response.
*   **Harmful Content Generation**: The system needs to handle prompts requesting harmful information (e.g., "What's the recipe for dynamite?").
    *   **Mitigation**: The system leverages the safety features of the LLM providers. Vertex AI has built-in safety filters that can flag harmful prompts. OpenAI provides a separate moderation API endpoint for similar capabilities, though it requires additional integration effort.

### 9. Training pipelines

The system does not involve model training but rather a RAG pipeline for indexing and inference.

*   **Tooling**:
    *   **Orchestration Framework**: Langchain, specifically the `ConversationalRetrievalQAChain` class.
    *   **Programming Language**: JavaScript/TypeScript (`[inferred]` from code snippets).
    *   **LLM Providers**: Google Vertex AI (Chat Bison), OpenAI (ChatGPT 3.5/4), Azure OpenAI.
    *   **Embedding Models**: `OpenAIEmbeddings` is mentioned in a code snippet.
    *   **Vector Store**: HNSWLib (local disk implementation).
    *   **Deployment Platform**: Google Cloud Platform (GCP).
*   **Automation**:
    *   The data indexing pipeline is automated to keep the vector store in sync with the Zendesk Help Center via webhooks.
    *   Authentication with Google Vertex AI is handled automatically using GCP's Workload Identity, avoiding the need to manage API keys.

### 10. Features

The "features" for this RAG system are the semantic representations of text chunks from the help articles.

*   **Feature Source**: The HTML body of articles from the Vimeo Help Center.
*   **Feature Engineering**:
    *   **Chunking**: Articles are split into smaller, semantically coherent chunks using HTML tags as delimiters. This enables the retrieval of more granular and relevant context for a given query.
*   **Feature Selection**:
    *   This is performed at inference time via semantic search. The user's query is embedded, and a similarity search is run against the vector store.
    *   The top-k most similar document chunks are retrieved and used as context for the LLM. The code snippet `vectorstore.asRetriever(5)` suggests that the top 5 chunks are retrieved.

### 11. Measuring results

#### 11.1. Offline evaluation methodology

The prototype was evaluated through a qualitative comparison of different LLM providers and models. The team assessed models based on response quality, conciseness, speed, cost, and available features like streaming. A speed comparison video was also created to demonstrate the latency differences between models.

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting format

The results of the evaluation led to the selection of Google Vertex AI Chat Bison as the preferred model for the prototype due to its concise responses, speed, and seamless integration with GCP. The findings were documented in the source blog post.

### 12. Integration and Serving

#### 12.1. API design

The system is designed as a conversational chat application. It maintains the chat history of the current session to understand the context of follow-up questions.

#### 12.2. Infrastructure

*   **Serving Architecture (RAG)**:
    1.  The user's question and chat history are combined.
    2.  An LLM call rephrases this into a standalone question.
    3.  The standalone question is embedded.
    4.  The vector store is queried to retrieve the top 5 relevant document chunks.
    5.  The retrieved chunks and the standalone question are passed to the final LLM in a structured prompt.
    6.  The LLM generates the final answer, which is returned to the user.
*   **Vector Store**: HNSWLib on a local disk was used for the prototype, with the flexibility to switch to other providers.
*   **Deployment**: The application is deployed on Google Cloud Platform.

#### 12.3. SLAs, latency budgets, and fallback strategies

*   **Latency**: Response time was a key evaluation metric. The code snippet for the Vertex AI model shows a `timeout` of 20,000ms (20 seconds). The choice between a model that streams tokens (ChatGPT) versus one that returns a complete response (Bison) involves a trade-off between time-to-first-token and total generation time.
*   **Fallback & Redundancy**: The architecture is designed to be model-agnostic, allowing for seamless switching between different LLM providers (e.g., Google, OpenAI, Azure). This provides redundancy in case of a provider outage.
*   **Safety Fallback**: For out-of-scope or harmful questions, the system falls back to a pre-defined response informing the user about the bot's limitations.

### 13. Monitoring

*   **Data Quality Monitoring**: The system uses a webhook from Zendesk to listen for changes in the Help Center articles. This ensures the vector store, which is the source of truth for the RAG system, remains up-to-date.
*   **Model Quality Monitoring**:
    *   The primary strategy to ensure consistent quality is setting the LLM `temperature` to 0, which makes responses more deterministic.
    *   The system leverages provider-side safety features (Vertex AI safety filters, OpenAI Moderation API) to flag and handle harmful or inappropriate user prompts. This can be used as a basis for monitoring malicious usage patterns.

### 14. Operations

*   **Retraining Cadence**: The system does not require "retraining." Instead, it has a continuous "re-indexing" process. The vector store is updated automatically via a Zendesk webhook whenever an article is created, updated, or deleted.
*   **Incident Response and Rollback**: The ability to switch between different LLM providers serves as a key incident response mechanism. If one provider experiences performance degradation or an outage, the system can be re-routed to another.
*   **Non-engineering Considerations**: The article suggests that the same architecture could be extended to create a unified search tool for internal employees, indexing documentation from various sources like GitHub, Confluence, Google Docs, and Zendesk.