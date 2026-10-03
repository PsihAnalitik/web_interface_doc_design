**Company**: Plaid
**Title**: How we use machine learning to power accurate, real-time income verification
**Technology Area**: Predictive ML
**Source URL**: https://plaid.com/blog/machine-learning-income-verification/
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The system, named Bank Income, is part of Plaid's suite of income verification products. It is designed to address the challenges in the lending process, where verifying a potential borrower's income is a critical but often time-consuming and error-prone task when using traditional methods like pay stubs or tax returns.

The Bank Income product uses machine learning to automatically identify and verify a borrower's income directly from their bank transaction data. The user flow is as follows:
1.  A consumer permissions Plaid to access their bank accounts.
2.  Plaid's ML models analyze transactions to detect potential income sources.
3.  The consumer is presented with these detected sources and selects which ones represent their income.
4.  Plaid provides the lender with the consumer-selected income sources, including metadata like category and frequency.

#### 1.2. Relevance & reasons

Traditional income verification is slow and manual. By automating the identification of income from bank transactions, Plaid aims to create a faster, more accurate, and streamlined underwriting process for lenders. This allows lenders to make more informed and quicker decisions about a borrower's creditworthiness. The system processes data from Plaid's connectivity to over 12,000 financial institutions.

#### 1.3. Expectations

The system is expected to identify and categorize income sources in a matter of seconds, providing a real-time experience for the end-user (the borrower). For the lender, the expectation is to receive an accurate and comprehensive view of a borrower's income streams. For the end-user, the experience should be streamlined to reduce the time and effort required to select their income sources.

#### 1.4. Previous work

Before the implementation of the current ML models, the system relied on simpler methods:
*   **Income Identification**: A heuristic-based system was used to rank income sources based on popular income categories and large transaction amounts. This required users to scroll through and manually examine each source.
*   **Income Categorization**: A system based on regex rules was used, leveraging in-house domain knowledge of bank transactions. This approach achieved high precision but suffered from low recall, as it struggled with the long-tail of income patterns that were hard to capture with fixed rules.

#### 1.5. Usage volumes and patterns

The system leverages Plaid's connectivity to over 12,000 financial institutions, implying a large and diverse set of transaction data sources.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Primary Goal**: Accurately identify and categorize a consumer's income sources from their bank transaction data in real-time.
*   **User Experience Goal**: Streamline the income selection process for the end-user, reducing selection time and cognitive load. An A/B test confirmed a 17% reduction in user selection time.
*   **Model Performance Goals**:
    *   Increase the recall of income categorization, particularly for key categories like `SALARY`. The system achieved a 24% increase in salary recall post-launch.
    *   Achieve high accuracy in frequency detection. The system reports a 95% detection rate for salary streams and 97% for government-related income streams.
    *   Effectively identify high-income sources.

#### 2.2. Anti-goals

*   The system should not overwhelm the user by presenting all potential source streams for selection.
*   Streamlining the user experience should not come at the cost of accuracy or completeness. The total income amount and number of streams shared by the user should remain consistent, which was confirmed via A/B testing.
*   The system should not sacrifice significant precision for recall gains. A "sweet spot" is actively sought to balance this trade-off.

### 3. Risks and constraints

*   **Data Quality**: The system relies on labels derived from user behavior (for income identification) and manual annotation (for categorization), both of which are prone to noise.
    *   Users may incorrectly select all available sources to rush the process.
    *   Users may attempt to inflate their income for credit approval.
    *   Manual labels can contain errors due to human factors like randomness, changing guidelines, or subjective interpretation.
*   **Data Complexity**:
    *   The "long-tail problem" where many income sources do not have obvious, recurring patterns, making them difficult to identify with simple rules.
    *   Ambiguity in transaction data, such as in shared joint accounts where only one person's salary is relevant for a given application.
    *   Sources like `TRANSFER` and `CASH_DEPOSIT` are sometimes valid income (e.g., for small business owners) but often are not, creating classification challenges.
*   **Model Degradation**: The system is susceptible to performance degradation over time due to data drift and concept drift ("parameter jumps").

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Income Identification Model (IIM)**:
    *   **Average Precision (AP)**: Used to summarize the precision-recall (PR) curve.
    *   **Dollar Amount Weighted AP**: A custom metric that gives more weight to the correct identification of high-income sources.
*   **Income Categorization Model (ICM)**:
    *   **Average Precision (AP)**: Used to evaluate performance per category. Achieved an AP of 0.969 for `SALARY` and 0.739 for `LONG_TERM_DISABILITY` on test data.
    *   **Weighted AP**: Gives more weight to sources with larger amounts.
    *   PR curves are analyzed for each of the 13 categories to determine optimal classification thresholds.
*   **Frequency Detection Model**:
    *   **Frequency Detection Rate**: Measures the percentage of streams for which frequency is correctly identified. The model achieves 95% for salary and 97% for government-related income.
*   **Label Enhancement Model**:
    *   **Label Error Reduction**: Measured an 80% reduction in label errors through independent validation.

#### 4.2. Online/business metrics

*   **User Selection Time**: The time it takes for a user to complete the income selection step. A 17% reduction was measured in an A/B test.
*   **Total Income Shared**: The total dollar amount of income the user consents to share. This was kept consistent in the A/B test.
*   **Salary Recall**: The percentage of actual salary streams correctly categorized as `SALARY`. A 24% increase was observed after launching the ICM.
*   **Categorization Rate**: The percentage of user-selected income sources that are successfully categorized.

#### 4.3. Loss functions

[NO INFO] (The source mentions using XGBoost classifiers, which typically optimize for log loss in classification tasks, but the specific loss function is not stated).

### 5. Data (Dataset)

#### 5.1. Data sources

The primary data source is consumer-permissioned bank transaction data from over 12,000 financial institutions connected via Plaid.

#### 5.2. Labeling strategy

*   **Income Identification Model (IIM)**: Uses proxy labels. A transaction stream is labeled as "income" if the user selects it to be shared with the lender. This is considered the ground truth, despite containing some noise.
*   **Income Categorization Model (ICM)**: Uses manually labeled income sources to train the model and monitor its performance.

#### 5.3. Data quality and cleaning

*   **Initial Filtering**: Transactions that are clearly not income, such as account transfers and reverse charges, are filtered out early in the pipeline.
*   **IIM Training Data Cleaning**:
    *   Erroneous selections (e.g., users who select every available source) are filtered out during data preprocessing.
    *   Users with fewer than three income streams are removed from the training set, as the streamlined UI provides little utility for them.
*   **ICM Label Enhancement**: An ML-based "Label Enhancement" model was developed to identify and rectify incorrect manual labels. This process reduced label errors by an estimated 80%.

#### 5.4. ETL

The overall data processing pipeline is a sequence of steps:
1.  **Transaction Extraction**: Pull transactions from user's bank accounts.
2.  **Filtering**: Remove non-income transactions.
3.  **Clustering**: A clustering algorithm groups similar transactions into "source streams" (e.g., grouping all paychecks from one employer).
4.  **Feature Generation**: Various features are generated for each source stream.

### 6. Validation schema

*   **Train/Test Split**: The models are evaluated on a held-out test set. For the ICM, specific AP metrics on test data are reported.
*   **Cross-Validation**: Used during the development of the ICM for "rigorous hyperparameter tuning."
*   **Bucket Analysis**: For the IIM, performance is analyzed across different income amount buckets (e.g., `< $2.5k`) by comparing PR curves to identify areas of weakness.
*   **Temporal Considerations**: The data is described as being "sampled from a historical time period," which suggests a time-based splitting strategy to prevent data leakage, though details are not provided.

### 7. Baseline solution

*   **Income Identification**: The baseline was a set of "simple heuristics" that ranked potential income sources using popular income categories and large transaction amounts. This forced users to manually review a potentially long list.
*   **Income Categorization**: The baseline was a system of "regex rules" built on internal domain expertise. It achieved high precision but had low recall and struggled with the long-tail of diverse income patterns.

### 8. Errors and their analysis

*   **Problem Formulation Error**: An initial approach to treat identification and categorization as a single hierarchical classification problem failed. Data analysis showed that the user's decision to select a stream (identification) is independent of its formal category. For example, users in a joint account might not select a valid `SALARY` stream, while a small business owner might select a `TRANSFER` stream as valid income. This led to splitting the problem into two separate models: IIM and ICM.
*   **IIM Model Errors**: The model shows diminished performance for income sources with small amounts (under $2.5k). This is attributed to the "noisy nature of non-recurring sources" like gig economy payments or Zelle transfers, which are difficult to distinguish from non-income transactions.
*   **ICM Model Errors**: The previous rule-based system had low recall (a type of error). The ML model addresses this by accepting a small drop in precision for a large gain in recall. This trade-off is managed by analyzing PR curves for each category and setting an appropriate probability threshold to find a "sweet spot."
*   **Labeling Errors**: A significant source of error was noisy labels, both from user selections and manual annotation. This was addressed by implementing data cleaning steps and a dedicated Label Enhancement model.

### 9. Training pipelines

*   **Tooling**:
    *   **Models**: XGBoost is used for both the Income Identification Model (binary classifier) and the Income Categorization Model (multi-class classifier).
    *   **Frequency Detection**: A hybrid approach combining frequency rules and a Variable Frequency Detection (VFD) algorithm based on auto-regression.
*   **Architecture**: A unified training architecture was designed to maximize code reusability between the IIM and ICM. Shared logic and modules, such as for text embedding featurization, are maintained in common abstractions to ensure consistency and streamline development. (see image: `Figure 5. Modeling design`).
*   **Automation and CI/CD**:
    *   A model retraining pipeline is implemented with hyperparameter tuning enabled.
    *   After each retraining job, an automated evaluation step compares the new model's performance against the previous version.
    *   This comparison informs the decision of whether to promote the new model to production.

### 10. Features

A variety of featurization techniques are used to handle the mixed data types in the source stream dataset.
*   **Transaction Description Embedding**: "Classic embedding techniques" are used to convert textual transaction descriptions into numerical representations that capture semantic meaning.
*   **Categorical Data Featurization**: Standard encoding is applied to categorical fields like `frequency` and `financial institutions`. High-cardinality features undergo additional processing to reduce dimensionality and prevent overfitting.
*   **Time Series Featurization**: Statistical measures (e.g., mean, std dev) are extracted from the time series of transaction dates and amounts within each stream. There are plans to incorporate more "advanced temporal patterns" in the future.
*   **Source Context Featurization**: Features are engineered to capture the context of a source stream relative to other streams for the same user. For example, a feature might represent the percentage of a user's total income that comes from a specific stream, capturing its relative importance.

### 11. Measuring results

*   **Offline Evaluation**: Model performance is evaluated on a held-out test set using AP and weighted AP metrics. PR curves are used for detailed analysis and threshold tuning.
*   **A/B Testing**: The impact of the IIM-powered streamlined user experience was measured via a production A/B test.
    *   **Hypothesis**: The new experience would reduce user selection time without negatively impacting the total income amount shared.
    *   **Outcome**: The test was successful, showing a 17% reduction in selection time while the total income shared remained consistent.
*   **Reporting**: The production launch of the ICM was measured by its impact on business metrics. It resulted in a 24% increase in salary recall and a significant increase in the overall categorization rate of selected income.

### 12. Integration and Serving

*   **Serving Architecture**: The system is a multi-stage pipeline of models that runs in real-time during the Plaid Link user flow. (see image: `Figure 2. Family of ML models that powers Bank Income`).
    1.  **Clustering**: Groups transactions into source streams.
    2.  **Frequency Detection**: Assigns a recurrence frequency to each stream.
    3.  **Income Identification Model (IIM)**: Predicts the probability that a user will select a stream as income. This probability is used to power a "streamlined experience" that prioritizes or pre-selects likely income sources.
    4.  **Income Categorization Model (ICM)**: Assigns one of 13 income categories (e.g., `SALARY`, `GIG_ECONOMY`) to each stream.
*   **API**: The final output is delivered to the lender, containing the list of user-selected income sources along with metadata including the predicted category and frequency for each stream.
*   **SLAs**: The entire process is designed to complete "in a matter of seconds" to ensure a smooth real-time user experience.
*   **Fallback Strategy**: The system can be seen as a hybrid model. The ML-based categorization model was launched to improve upon an existing rule-based system. The analysis of PR curves to set thresholds suggests that for some predictions below a certain confidence, the system might fall back to a "no category" state or a different logic, though this is not explicitly stated.

### 13. Monitoring

*   **Model Performance Degradation**: The system is monitored for "data drift and parameter jumps" that could degrade performance.
*   **Retraining and Evaluation**: The retraining pipeline includes a mandatory evaluation step where a newly trained model's performance is compared against the currently deployed version. This serves as a gate for model promotion and a key monitoring tool.
*   **Ground Truth Monitoring**: The ICM's performance is monitored using a continuously growing dataset of manually labeled income sources.

### 14. Operations

*   **Retraining Cadence**: A retraining pipeline is in place to allow the model to learn from new data over time. The exact cadence is not specified.
*   **Model Promotion**: A new model is promoted to production only after an evaluation step confirms its performance is superior to the previous version. This suggests a formal review and promotion process.
*   **Incident Response and Rollback**: The model promotion process, which compares new and old versions, implies that a rollback to the previous model version is possible if the new model causes issues in production.