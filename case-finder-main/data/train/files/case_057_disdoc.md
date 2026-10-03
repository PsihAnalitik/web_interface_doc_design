**Company**: Whatnot
**Title**: Enhancing Search Using Large Language Models
**Technology area**: Generative AI & LLM
**Source URL**: https://medium.com/whatnot-engineering/enhancing-search-using-large-language-models-f9dcb988bdb9
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The system addresses shortcomings in the text input processing of Whatnot's e-commerce search functionality. Users' search queries often contain misspellings or abbreviations, which the existing search system failed to interpret correctly. This leads to a poor user experience where users might incorrectly assume the platform lacks certain items.

#### 1.2. Relevance & reasons

Failing to comprehend user input accurately leads to poor search results and negative user perceptions. For example:
*   **Misspellings**: A search for "jewlery" (a common misspelling of "jewelry") would return a nearly empty search results page (SERP), leading users to believe Whatnot has no jewelry-related content. Correcting the query to "jewelry" provides an extensive results page with relevant categories, live shows, and products, leading to better discovery, engagement, and purchases.
*   **Acronyms/Abbreviations**: Queries for acronyms like "lv" (for "Louis Vuitton") or "nyfw" (for "New York Fashion Week") resulted in a low count of results and lower downstream engagement rates.

The goal is to improve search recall and relevance for these types of queries to better serve users' high-intent discovery needs.

#### 1.3. Expectations

The primary expectation is to provide relevant content for misspelled queries and queries containing abbreviations, thereby improving the overall search experience. A critical product expectation is maintaining low search latency. The user value of search is heavily dependent on speed, with an ideal target of sub-250ms response time.

#### 1.4. Previous work

The article mentions a "previous query expansion method" that the new GPT-based approach is compared against. The new system yielded "substantial improvements in query expansion accuracy" and "streamlined the generation and serving process significantly" compared to this prior method.

#### 1.5. Usage volumes and patterns

[NO INFO]

### 2. Goals and anti-goals

#### 2.1. Goals

*   Accurately detect and rectify misspelled words in search queries.
*   Expand acronyms and abbreviations to their full-text equivalents (e.g., "sdcc" to "san diego comic con").
*   Reduce the amount of irrelevant content shown for queries containing misspellings or abbreviations.
*   Improve downstream user engagement and purchase rates for affected queries.

#### 2.2. Anti-goals

*   The system must not introduce significant latency into the search request path. Real-time calls to a large language model like GPT are explicitly avoided to meet the sub-250ms latency target. The solution uses an offline-generated cache to ensure low latency at serving time.

### 3. Risks and constraints

*   **Latency Constraint**: The search experience has a strict latency budget, ideally under 250ms. This constrains the architecture to an offline generation and online caching/lookup pattern, avoiding real-time LLM inference.
*   **Model Dependency**: The system relies on an external LLM (GPT). Changes to the model's behavior, cost, or availability could impact the quality and feasibility of the query expansion generation process.
*   **Over-correction Risk**: The LLM might incorrectly "correct" legitimate but obscure terms, brand names, or slang as misspellings. The article notes that GPT handles real-world entities like "Xero" (shoes) or "MSCHF" well, mitigating this risk without needing a dedicated knowledge graph.
*   **One-Way Expansion**: The current implementation is token-specific and one-directional. It can expand "sdcc" to "san diego comic con" but cannot do the reverse. This is a known limitation.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Query Expansion Accuracy**: The primary offline metric is the accuracy of the generated spelling corrections and abbreviation expansions.
*   **Irrelevant Content Reduction**: For queries containing misspellings or abbreviations, the system measured a reduction in irrelevant content by "more than 50%" compared to the previous method.

#### 4.2. Online/business metrics

*   **Downstream Engagement Rates**: The system aims to improve user engagement on the SERP, which is tracked via event logs. Low engagement was a key indicator of the problem for abbreviation queries.
*   [inferred] Click-through rate (CTR) on search results.
*   [inferred] Conversion rate from search.

#### 4.3. Loss functions

[NO INFO] (The system uses a pre-trained GPT model via prompting, not fine-tuning, so no loss function is described).

### 5. Data (Dataset)

#### 5.1. Data sources

The primary data source is user search query logs from the Whatnot backend. The system logs every search performed, including:
*   The raw query string.
*   Any filters applied.
*   The Search Engine Results Page (SERP) tab the user lands on (e.g., Products, Shows, Users).

These event logs can be joined in a data warehouse to analyze user behavior at three levels:
*   **SERP tab session**: Actions on a specific SERP tab for a given query.
*   **Query session**: Actions for a specific query across multiple SERP tabs.
*   **Search session**: Continuous user engagement with search, including navigation and re-querying.

#### 5.2. Labeling strategy

There is no explicit labeling strategy. The system uses GPT's existing knowledge to generate corrections and expansions, which are then used as "labels" or targets for the query expansion cache.

#### 5.3. Data quality and cleaning

A simple text processing pipeline is used for normalization before analysis and processing:
*   **Normalization**: All queries are converted to lowercase. Punctuation and emojis are standardized or removed. This ensures queries like "Ipad Air", "iPad air", and "ipad Air" are all treated as "ipad air".
*   **Tokenization**: Queries are broken down into individual tokens by splitting on white spaces. For example, "ipad air" becomes two tokens: "ipad" and "air".

#### 5.4. ETL

The process for selecting tokens to be enriched by GPT is as follows:
1.  Aggregate search query logs over the past 14 days.
2.  Count the frequency of each normalized token.
3.  Select tokens that have been used more than 3 times during this period for the subsequent GPT rectification step.

### 6. Validation schema

[NO INFO]

### 7. Baseline solution

A "previous query expansion method" existed before the GPT-based solution. The details of this method are not provided, but it served as the baseline for comparison. The new approach was found to provide "substantial improvements in query expansion accuracy" and reduced irrelevant content by over 50% relative to this baseline.

### 8. Errors and their analysis

The primary errors the system is designed to solve are:
*   **Misspellings**: Users typing queries like "jewlery" instead of "jewelry".
*   **Unexpanded Acronyms/Abbreviations**: Users typing queries like "lv" or "nyfw" and not getting results for "Louis Vuitton" or "New York Fashion Week".

The analysis of the solution identified a key limitation:
*   **Asymmetric Expansion**: The current token-based approach is one-way. A search for "sdcc" is expanded to include results for "san diego comic con", but a search for "san diego comic con" is not expanded to include results for "sdcc". The article suggests two potential solutions for this:
    1.  Apply the same expansion process at indexing time.
    2.  Perform GPT rectification on n-grams instead of just unigrams.

### 9. Training pipelines

The system uses an offline generation process, which is analogous to a training pipeline. This process is run on an ad-hoc or scheduled basis and is not in the production request path.

The pipeline consists of the following steps:
1.  **Data Collection**: Collect search queries from event logs.
2.  **Tokenization**:
    *   Normalize queries (lowercase, remove punctuation/emojis).
    *   Tokenize queries into unigrams by splitting on whitespace.
    *   Filter for frequently occurring tokens (used >3 times in the last 14 days).
3.  **GPT Rectification**:
    *   Send the filtered, frequent tokens to a GPT model.
    *   Use a prompt designed to identify potential misspellings and suggest expansions for acronyms/abbreviations.
4.  **Post-processing**:
    *   Receive spelling corrections and abbreviation expansions from the GPT model.
    *   Store these mappings in a "query expansion cache," which is a production-level key-value store. The cache maps original tokens to a list of potential corrections/expansions with associated confidence levels.

### 10. Features

The primary "features" are the tokens (unigrams) extracted from user search queries.

*   **Feature Source**: Raw user search queries from logs.
*   **Feature Engineering**:
    *   Lowercasing.
    *   Punctuation and emoji removal/standardization.
    *   Splitting by whitespace.
*   **Feature Selection**: Only tokens that appear more than 3 times in a 14-day period are selected for processing by GPT. This acts as a filter to focus on frequently used terms and manage costs/complexity.

### 11. Measuring results

#### 11.1. Offline evaluation

The performance of the new system was compared to the previous query expansion method. The key result was a reduction of "irrelevant content by more than 50%" for queries containing misspellings or abbreviations.

#### 11.2. A/B testing

[NO INFO] (While online metrics like engagement are mentioned, the article does not describe a specific A/B testing framework).

#### 11.3. Reporting

[NO INFO]

### 12. Integration and Serving

The system uses a hybrid offline/online architecture to meet latency requirements.

#### 12.1. API design and serving pattern

*   **Serving Pattern**: Online, synchronous serving via a cache lookup.
*   **Architecture**:
    1.  At request time, the incoming user query is tokenized using the same logic as the offline pipeline.
    2.  The system performs a lookup in the "query expansion cache" (a production key-value store) for each token.
    3.  If expansions or corrections are found, they are used to augment the query. The article mentions this is done by augmenting the query's "S-expression".
    4.  The final search result page is generated from the combination of the original query and the expanded query terms.

#### 12.2. Infrastructure

*   **Offline**: The GPT rectification process runs on an ad-hoc/scheduled basis outside the production path.
*   **Online**: A "production-level key-value store" is used as the query expansion cache to ensure low-latency lookups.

#### 12.3. SLAs and fallback

*   **SLA**: The target latency for the search experience is "ideally sub-250ms".
*   **Fallback**: If a token is not found in the query expansion cache, the system [inferred] proceeds with the original token without expansion. The search function does not fail.

### 13. Monitoring

*   **Data Quality**: The system logs every search query, filters, and SERP tab interaction. This data is stored in a data warehouse and used for offline analysis of user behavior (e.g., engagement rates) and to feed the offline generation pipeline.
*   **Model Quality**: [NO INFO]
*   **Engineering Metrics**: [NO INFO] (Although latency is a key constraint, specific monitoring for it is not described).

### 14. Operations

*   **Retraining Cadence**: The query expansion cache is updated "on an ad hoc/scheduled basis" by running the offline generation pipeline. The exact frequency is not specified.
*   **Incident Response**: [NO INFO]
*   **Ownership**: The work was done by a Search Engineer and a Machine Learning Scientist.
*   **Non-engineering considerations**: [NO INFO]