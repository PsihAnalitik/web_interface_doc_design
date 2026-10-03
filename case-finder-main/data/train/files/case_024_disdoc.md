- Company: Walmart
- Title: Using Predictive and Gen AI to Improve Product Categorization at Walmart
- Technology area: Generative AI & LLM
- Source URL: https://medium.com/walmartglobaltech/using-predictive-and-gen-ai-to-improve-product-categorization-at-walmart-dc9821c6a481
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The problem originates from the need to organize Walmart's vast online catalog of over 400 million SKUs to enhance the customer shopping experience on its digital platforms (website and mobile apps). The goal is to mirror the organized, aisle-based layout of physical Walmart stores in the digital realm.

The product catalog has two main hierarchical structures:
1.  **Category Tree**: A customer-facing hierarchy that organizes products into departments and sub-departments. Deeper navigation leads to more specific results. Example: `Toys → Outdoor Toys → Pool Toys`.
2.  **Product Type**: An internal classification that helps in understanding the intended use of each item. It is not displayed directly on the website. Example: A screwdriver for a dentist is "Oral Care Accessories," while one for electronics is a "Screwdriver Tool."

#### 1.2. Relevance & reasons

Effective categorization is crucial for saving customers' time and making their online shopping experience more efficient and enjoyable. When a customer browses a category, the system must display the most relevant items. The current process for this is:
1.  Fetch all items belonging to the browsed category.
2.  Identify the relevant 'Product Types' for that category.
3.  Filter the items from step 1, showing only those that match the identified product types.

This project, named **Ghotok**, focuses on improving step 2. With a large number of categories and SKUs, items can be mistakenly categorized, leading to less pertinent items being shown to customers. Ghotok is an AI system designed to accurately determine the many-to-many relationships between 'Categories' and 'Product Types'.

#### 1.3. Expectations

The system is expected to make the online shopping journey "smooth and effortless" and save customers "precious time." The core technical expectation is for Ghotok to accurately map relevant Product Types to each Category, ensuring that product listings within a category are uniform and relevant.

#### 1.4. Previous work

The article describes the existing backend logic that Ghotok was designed to improve. This logic involves a three-step filtering process based on category and product type. Ghotok is presented as a "state-of-the-art AI technique" to enhance the second step of this existing flow, which is identifying relevant product types for a given category.

#### 1.5. Usage volumes and patterns

-   **SKUs**: Over 400 million.
-   **Categories**: "Several thousand".
-   **Product Types**: Each category can correlate with "hundreds" of different Product Type nodes.
-   **Candidate Pairs**: The combination of categories and product types results in "several million rows of offline data" representing potential `<Category, ProductType>` mappings.

### 2. Goals and anti-goals

#### 2.1. Goals

-   **Primary Business Goal**: To save customers' time and make their online shopping experience more efficient and fun.
-   **Primary ML Goal**: To accurately model the many-to-many relationships between the 'Category' and 'Product Type' hierarchies, finding the most relevant product types for each category.
-   **System Goal**: To group products as uniformly as possible within each category.
-   **Performance Goal**: To achieve a "satisfactory level" for the False Positive Rate (FPR), minimizing the number of irrelevant product types associated with a category.

#### 2.2. Anti-goals

-   The system explicitly avoids using customer engagement data (e.g., clicks) for training. This data is considered "noisy" because customers might click on items by mistake or out of curiosity. The model should be effective for both frequently and rarely visited parts of the product hierarchy.

### 3. Risks and constraints

#### 3.1. Risks

-   **Miscategorization**: The primary risk is incorrectly mapping Product Types to Categories, which would result in showing less pertinent items to customers.
-   **GenAI Hallucination**: While the system uses GenAI, the article states that hallucination is not a significant issue because GenAI is used in a targeted way to filter false positives from predictive models, leveraging its semantic understanding rather than for open-ended generation.
-   **Production Edge Cases**: After deployment, unforeseen edge cases could lead to poor recommendations. An exception handling tool was built to mitigate this risk.

#### 3.2. Constraints

-   **Scale**: The system must handle a massive catalog with over 400 million SKUs and millions of potential `<Category, ProductType>` pairs.
-   **Cost**: Inference with large Generative AI models is costly. The system is designed to mitigate this by using GenAI only on a small, pre-filtered subset of candidate pairs.
-   **Latency**: The backend serving system has a strict Service Level Agreement (SLA) of "a few milliseconds" for responding to user requests.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The following metrics are used to evaluate the predictive AI models and select the best hyperparameters on a human-labeled dataset:
-   `precision`
-   `recall`
-   `f1`
-   `true positive rate (TPR)`
-   `false positive rate (FPR)`

The FPR is specifically used to set confidence thresholds for filtering candidate pairs.

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

-   **Primary Data**: Walmart's product catalog, which contains the 'Category' and 'Product Type' hierarchies.
-   **Features**: The predictive models are trained on "domain-specific features". The generative models use the full hierarchical path of categories and product types as input.
-   **Labels**: A "limited amount of human-labeled data" is used for training and hyperparameter tuning of the predictive models.

#### 5.2. Labeling strategy

A human-labeled set of `<Category, ProductType>` pairs is used to train the predictive models. This approach was chosen to avoid using noisy customer clickstream data.

#### 5.3. Available metadata

The system uses the full hierarchical path for both categories and product types, represented as a string (e.g., `Toys → Outdoor Toys → Pool Toys`). This "root-to-the-node" representation is considered essential for providing context to the Generative AI models.

#### 5.4. Data quality issues

-   Some items in the catalog are "mistakenly categorized."
-   Customer engagement data (clicks) is considered "noisy" and unreliable for this task.

#### 5.5. ETL

[NO INFO]

### 6. Validation schema

#### 6.1. Train/validation/test split strategy

-   A "human-labeled set" is used for training the predictive models and choosing hyperparameters.
-   A "validation set" was used to confirm that the final ensemble of predictive and generative AI models achieved the best performance.

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets

[NO INFO]

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

The Ghotok system is an ensemble model that improves upon a simpler, high-recall first stage. The predictive AI models can be considered the baseline component of the system.

1.  **Baseline (Predictive AI Models)**: An ensemble of predictive AI models (million-parameter models) are trained on domain-specific features. These models generate millions of candidate `<Category, ProductType>` pairs. This stage is optimized for recall at a certain FPR.
2.  **Advanced Solution (Generative AI Refinement)**: The thousands of candidate pairs that pass the predictive models' confidence thresholds are then passed to Generative AI models (billion-parameter models) for a final filtering step. This stage acts as a high-precision refiner to eliminate false positives.

### 8. Errors and their analysis

#### 8.1. Error taxonomy

The primary error type addressed is **False Positives**: identifying an irrelevant `ProductType` as relevant for a given `Category`. The entire system is designed as a cascade to reduce the False Positive Rate (FPR) to a satisfactory level.

#### 8.2. Residual analysis

The system design inherently performs a type of residual analysis. The Generative AI stage is specifically used to "eliminate false positives from the predictive AI methodologies." This implies that the errors (false positives) of the first-stage models are the specific targets for the second-stage models.

#### 8.3. Diagnostic approaches

-   **GenAI Hallucination Management**: Hallucination is managed by using GenAI models in a constrained classification/filtering task rather than for open-ended generation. The models leverage their "advanced semantic comprehension" to identify mismatches.
-   **Post-Deployment Exception Handling**: An "exception handling tool" was developed to manage edge cases in production. This tool is powered by both machine learning and human intervention, allowing for "swift and seamless resolution" of issues.

### 9. Training pipelines

#### 9.1. Tooling

[NO INFO]

#### 9.2. Preprocessing, training, evaluation, and deployment automation

The system follows a multi-stage process:

1.  **Predictive AI Model Training**:
    -   Multiple predictive AI models are trained on "domain-specific features."
    -   Hyperparameters are selected based on performance (precision, recall, f1, etc.) on a human-labeled dataset.

2.  **Candidate Filtering (Stage 1 - Predictive)**:
    -   For each predictive model, a confidence threshold is learned by fixing a specific False Positive Rate (FPR).
    -   These models and thresholds are used to filter the initial "millions" of candidate `<Category, ProductType>` pairs down to "thousands."

3.  **Candidate Filtering (Stage 2 - Generative)**:
    -   The reduced set of candidate pairs is passed to Generative AI models.
    -   These models use techniques like **Chain-of-Thought (CoT)** prompting and **Symbol Tuning** to assess relevance.
    -   The GenAI models are not trained on domain-specific features but are prompted to leverage their existing knowledge.
    -   Learned relevance thresholds for the GenAI models are used to perform the final filtering.

The final output is a set of validated `<Category, ProductType>` mappings.

#### 9.3. Experiment tracking and CI/CD

[NO INFO]

### 10. Features

#### 10.1. Feature categories

-   **For Predictive AI Models**: "domain-specific features." [inferred] These likely include textual information from product titles and descriptions, and structured attributes.
-   **For Generative AI Models**: The primary feature is the full hierarchical path of the category and product type, provided as a string. For example: `root → category_level_1 → category_level_2`.

#### 10.2. Feature store or batch/offline computation patterns

[NO INFO]

#### 10.3. Feature importance and selection

-   Using the "entire path representation (root-to-the-node) as a string, rather than just context node names, proved essential" for the GenAI models.
-   **Symbol Tuning** was used to instruct the GenAI model to give "higher importance to the leaf node" of the hierarchy during relevance assessment, which led to a marked improvement in quality.

### 11. Measuring results

#### 11.1. Offline evaluation methodology

The final ensemble of predictive and generative models was evaluated on a "validation set" and "showed the best performance." The system successfully lowered the False Positive Rate (FPR) to a "satisfactory level."

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting format and decision criteria

[NO INFO]

### 12. Integration and Serving

#### 12.1. API design, batch vs. online serving

The Ghotok system runs as a batch process to generate an offline dataset containing millions of rows of validated `<Category, Set<ProductType>>` mappings. This dataset is then loaded into a production backend system. The backend system uses this data in real-time to filter products in response to user requests on the website and mobile apps.

#### 12.2. Infrastructure

To meet low latency requirements, the backend serving system uses a **two-tier caching system** with an **LRU (Least Recently Used) caching mechanism**.
-   **L1 Cache**: A small, fast cache providing access times of "one or two cycles."
-   **L2 Cache**: A larger, slightly slower cache.
-   **Primary Storage**: If a mapping is not found in either cache (a cache miss), the system queries the primary storage where the full dataset is kept.

The processor first checks L1, then L2, and finally primary storage.

#### 12.3. SLAs, latency budgets, and fallback strategies

-   **SLA**: The backend system must meet typical service level agreements that "usually range in a few milliseconds."
-   **Fallback**: The caching system falls back to primary storage on a cache miss. For incorrect predictions that make it to production, an exception handling tool provides a fallback mechanism involving human intervention.

#### 12.4. Release cycle for models vs. infrastructure

[NO INFO]

### 13. Monitoring

#### 13.1. Data quality and schema checks

[NO INFO]

#### 13.2. Model quality and prediction drift

[NO INFO]

#### 13.3. Input/target drift detection methods and thresholds

[NO INFO]

#### 13.4. Engineering metrics (latency, error rate, cost)

[NO INFO]

#### 13.5. Alerting and tooling

The primary tool mentioned for handling production issues is an **exception handling tool**. This tool is used to identify and resolve edge cases and is powered by both machine learning and human intervention. This implies a monitoring and alerting component that feeds into this tool.

### 14. Operations

#### 14.1. Day-to-day operational procedures

[NO INFO]

#### 14.2. Retraining cadence

[NO INFO]

#### 14.3. Incident response and rollback procedures

-   **Incident Response**: An "exception handling tool" is in place to manage post-deployment issues. This tool facilitates "swift and seamless resolution" of problems through a combination of ML and human-in-the-loop processes.

#### 14.4. Non-engineering considerations

[NO INFO]