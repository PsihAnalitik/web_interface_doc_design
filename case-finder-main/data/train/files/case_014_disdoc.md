**Company**: Picnic
**Title**: Enhancing Search Retrieval with Large Language Models (LLMs)
**Technology area**: Search Retrieval, LLM
**Source URL**: https://blog.picnic.nl/enhancing-search-retrieval-with-large-language-models-llms-7c3748b26d72
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

Picnic is an online grocery delivery service where customers order from a mobile application. The core problem is to enhance the product and recipe search retrieval system to make it easier for customers to find what they need. The challenge lies in accommodating tens of thousands of products within a small mobile interface and serving a diverse customer base across the Netherlands, Germany, and France.

#### 1.2. Relevance & reasons

The search function is a critical tool for navigating Picnic's broad product and recipe assortment. Customers use millions of different search terms, which presents a significant engineering challenge. The system must handle a wide variety of user behaviors and query imperfections, including:
*   **Spelling mistakes**: e.g., "jogurt" instead of "yogurt".
*   **Typos**: e.g., double whitespaces, accidental characters.
*   **Ambiguous intent**: e.g., a search for "ice" could mean blocks of ice (which Picnic doesn't sell) or ice-making utilities (which it does).
*   **Multilingual and regional differences**: A search for 'fromage' has different expectations for a Dutch customer versus a French customer.

With customer expectations for search quality rising due to mainstream exposure to advanced AI like ChatGPT, providing a best-in-class search experience is crucial for a weekly-use service like grocery shopping.

#### 1.3. Expectations

*   **Speed**: Search results must appear extremely quickly, "as they type," to provide a fast and seamless shopping experience.
*   **Accuracy**: The system must accurately interpret user intent and deliver relevant results that meet customer needs.
*   **Reliability**: The service must be stable and consistently available.

#### 1.4. Previous work

The article describes enhancing an existing search system. It notes that historically, e-commerce search could be subpar, but today's standards are much higher. The new LLM-based system is an improvement upon a pre-existing solution, which is later described as a "literal search" approach [inferred].

#### 1.5. Usage volumes and patterns

*   **Users**: Millions of customers across the Netherlands, Germany, and France.
*   **Queries**: Millions of different search terms are used.
*   **Catalog**: Tens of thousands of products and recipes.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Business Goals**:
    *   Improve conversion rates by helping users find what they are looking for.
    *   Enhance the click-through rate (CTR) of search results.
    *   Boost overall customer satisfaction.
*   **System Goals**:
    *   Accurately interpret and process user queries, correcting for common errors like typos and vague inputs.
    *   Comprehend the context and intent of a query to deliver the most relevant products and recipes.
    *   Maintain a fast, low-latency response time for search results.

#### 2.2. Anti-goals

*   **Avoid high latency**: The system explicitly avoids a fully generative, conversational search interface in its first version because the slow response times of LLMs (which can take seconds) do not meet the user expectation of results appearing "as they type". Speed and reliability are prioritized over a chat-like experience.
*   **Avoid live LLM calls for every query**: To ensure low latency and manage costs, the system is designed to not call LLM APIs for every incoming search query during runtime.

### 3. Risks and constraints

*   **Technical Constraints**:
    *   **Latency**: Search results must be delivered with very low latency, faster than typical LLM generation times. This constraint drove the decision to precompute embeddings.
    *   **Search Index Dimensionality**: The chosen search engine, OpenSearch, has a maximum dimensionality of 1536 for efficient retrieval. This constrained the choice of embedding model.
*   **Dependencies**:
    *   **Third-Party API**: The system depends on OpenAI's APIs (`GPT3.5-turbo`, `text-embedding-3-small`). This introduces a risk of downtime or performance degradation. Intelligent management through caching is required to ensure 24/7 service uptime.
*   **Cost**:
    *   Using OpenAI APIs incurs a fee. Prompting and embedding millions of search terms is resource-intensive. Precomputation and caching are used to manage these costs.
*   **Data Constraints**:
    *   The ground truth for offline evaluation, derived from past search results, is acknowledged to be "not as clean as one might expect," limiting its reliability for fine-tuning.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Search Accuracy**: Evaluated during offline optimization by tweaking parameters and models. The specific metric (e.g., NDCG, Recall) is not named.
*   **Search Speed**: The performance impact of different configurations is evaluated offline.

#### 4.2. Online/business metrics

*   **Conversion Rate**: To measure if users are more successful in finding and purchasing products.
*   **Click-Through Rate (CTR)**: A direct measure of how compelling and relevant the search results are.
*   **Customer Satisfaction**: The ultimate goal, measured through user interactions and feedback [inferred].

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **User Queries**: Historical search terms from millions of customers. The system precomputes embeddings for 99% of these past search terms.
*   **Item Catalog**: Content (e.g., descriptions) for tens of thousands of products and recipes in Picnic's assortment.

#### 5.2. Labeling strategy

The system uses implicit feedback from past user behavior as a proxy for ground truth during offline evaluation. The article notes that this data ("past search results") is not perfectly clean. For online evaluation, user interactions (clicks, conversions) in A/B tests serve as the label source.

#### 5.3. Data quality issues

*   **Query Imperfections**: User queries suffer from spelling mistakes, typos, extra whitespace, and random characters.
*   **Query Ambiguity**: Queries can be vague (e.g., "ice") or have different meanings based on user context (e.g., language, region).
*   **LLM Output Variability**: Outputs from language models can vary with updates and model iterations, requiring sanity checks.

#### 5.4. ETL

The core data processing is a precomputation pipeline that generates and stores embeddings:
1.  Historical search terms are processed.
2.  Product and recipe content is processed.
3.  An LLM-based pipeline generates embeddings for both queries and items.
4.  The generated embeddings are stored in OpenSearch.

### 6. Validation schema

The project follows a two-stage validation process:

1.  **Offline Optimization**:
    *   An initial phase where search parameters, LLM configurations (prompts, dimension size), and different models are experimented with.
    *   This is done in a simulated environment using historical search data to find the most effective strategies without impacting production.
    *   This stage is primarily used for initial parameter tweaking due to the "unclean" nature of the ground truth data.

2.  **Online A/B Testing**:
    *   Following offline validation, new features are rolled out to a controlled group of real users.
    *   This allows for the collection of reliable data on how changes affect user behavior compared to the existing system.
    *   The team uses an iterative approach, making small, incremental changes based on A/B test results to optimize the system.

### 7. Baseline solution

The baseline is the existing search system that was in place before the LLM enhancements. The article implies this is a "literal search" system [inferred], likely based on keyword matching. The new LLM-based retrieval system is evaluated against this baseline in A/B tests. Future work considers hybrid approaches that combine this literal search with the new semantic search capabilities.

### 8. Errors and their analysis

#### 8.1. Error taxonomy

The primary source of errors is the user query itself. The system is designed to be robust against:
*   **Data Input Errors**: Spelling mistakes, typos.
*   **Semantic Errors**: Ambiguous queries where user intent is unclear.
*   **Contextual Errors**: Queries that depend on user-specific context like language or location.

#### 8.2. Diagnostic approaches

*   **Pipeline Sanity Checks**: The precomputation pipeline includes "numerous sanity checks" to maintain data integrity. This includes verifying that embeddings are consistent and have the appropriate length, which helps mitigate issues from LLM version updates.

### 9. Training pipelines

The system does not train an LLM from scratch but orchestrates API calls to pre-trained models in a precomputation pipeline.

*   **Tooling**:
    *   **LLM Provider**: OpenAI.
    *   **Prompt Generation Model**: `GPT3.5-turbo` is used for its balance of performance and speed compared to `GPT4-Turbo`.
    *   **Embedding Model**: `text-embedding-3-small` is used to generate embeddings. Its output dimensionality of 1536 matches the maximum efficient size in OpenSearch.
    *   **Search & Storage**: OpenSearch is used to store embeddings and serve retrieval requests.

*   **Pipeline Architecture**:
    1.  **Prompt Generation**: A search term is fed into `GPT3.5-turbo` using a prompt-based approach. This generates a richer, more descriptive text that captures the user's potential intent (e.g., turning "daughter's birthday" into a description of related products).
    2.  **Embedding Generation**: The generated description is converted into a vector embedding using `text-embedding-3-small`.
    3.  **Precomputation**: This process is run offline for 99% of historical search terms, as well as for all product and recipe content.
    4.  **Storage**: The precomputed embeddings are stored in OpenSearch indexes for fast retrieval.
    5.  **Quality Control**: Sanity checks are run on the generated embeddings to ensure consistency and correct format.

*   **Experiment tracking**: The offline optimization phase involves tweaking LLM configurations, prompts, and other parameters, which implies a form of experiment tracking to identify the best-performing settings.

### 10. Features

The primary features are dense vector embeddings representing the semantic meaning of queries and items.

*   **Feature Categories**:
    *   **Query Embeddings**: Generated from user search terms via the two-step prompt-generation and embedding process.
    *   **Item Embeddings**: Generated from the content of products and recipes in the catalog.

*   **Feature Selection Criteria**:
    *   The choice of `GPT3.5-turbo` was a trade-off between performance and speed, as it was found to be as effective as the slower `GPT4-Turbo` for this task.
    *   The choice of `text-embedding-3-small` was determined by the technical constraint of OpenSearch's 1536-dimension limit for efficient search.

*   **Feature Computation**:
    *   Features are precomputed in a batch process to ensure low latency at serving time.
    *   OpenSearch serves as the storage and retrieval engine for these embeddings, acting as a form of feature store. The article mentions using two separate indexes: one for search term embeddings and another for item embeddings.

### 11. Measuring results

#### 11.1. Offline evaluation

*   An initial development phase focused on extensive offline optimization.
*   This involved simulating search scenarios with historical data to tune LLM configurations (prompts, models) and search parameters.
*   It is acknowledged that this method is mainly for initial tuning, as the historical data is not a perfect representation of ground truth.

#### 11.2. A/B test design

*   **Methodology**: After offline tuning, changes are validated through online A/B tests where a new feature is exposed to a controlled group of users.
*   **Comparison**: The performance of the new system is compared against the existing system.
*   **Data Collection**: The tests collect data on how real users interact with the changes, providing a reliable source of information for optimization.
*   **Iteration**: The team follows an iterative process, making incremental improvements based on A/B test results. Future experiments planned include changing result ranking and testing hybrid search approaches.

### 12. Integration and Serving

#### 12.1. API design

The system exposes a low-latency online search endpoint for the mobile application.

#### 12.2. Infrastructure

*   **Search Engine**: OpenSearch is used for storing embeddings and performing fast nearest-neighbor search.
*   **Serving Architecture**: A precomputation strategy is central to the design. Embeddings for queries and items are generated offline and stored in OpenSearch. At serving time, the system performs a fast lookup and vector search instead of making live calls to the OpenAI API.
*   **Caching**: Caching mechanisms are implemented "throughout our system" to reduce computational load, manage costs, and handle dependencies on third-party services.

#### 12.3. Serving Flow [inferred]

1.  A user types a search query in the app.
2.  The system performs a lookup in an OpenSearch index to find the precomputed embedding for that search term.
3.  This query embedding is used to execute a k-NN (k-Nearest Neighbors) search against the item embeddings stored in a second OpenSearch index.
4.  The top-k most relevant products and/or recipes are returned to the user.

#### 12.4. SLAs, latency budgets, and fallback strategies

*   **Latency**: The system is designed for "milliseconds of latency" for retrieval from OpenSearch, enabling a "search-as-you-type" experience.
*   **Availability**: A key goal is ensuring 24/7 service uptime.
*   **Fallback Strategy**: Caching helps manage the dependency on the OpenAI API, providing a fallback mechanism in case of API unavailability. The potential for a hybrid search (combining literal and semantic search) also offers a natural fallback or complementary retrieval strategy.

### 13. Monitoring

*   **Data Quality Monitoring**: The pipeline includes "numerous sanity checks" to verify the consistency and length of generated embeddings. This acts as a guard against quality degradation, especially when underlying LLM versions change.
*   **System Monitoring**: System stability and performance are carefully monitored, especially during the scaling phase when a new feature is rolled out to the entire user base.

[NO INFO] on model quality/drift monitoring or specific alerting tools.

### 14. Operations

*   **Retraining Cadence**: The article states that embeddings for 99% of historical search terms are precomputed. It does not specify the cadence for re-computing these embeddings or for updating item embeddings.
*   **Incident Response**: The use of caching to manage third-party dependencies is part of the operational strategy to maintain high availability.
*   **Rollout Strategy**: New features are rolled out progressively, starting with A/B tests and then scaling to the full user base upon demonstrated success.
*   **Future Considerations**: For a future, fully generative search UI, the team recognizes the need to involve designers to create a different user experience that can handle slower response times.