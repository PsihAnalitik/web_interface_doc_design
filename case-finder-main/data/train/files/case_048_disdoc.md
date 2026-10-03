**Company**: Netflix
**Title**: FM-Intent: Predicting User Session Intent with Hierarchical Multi-Task Learning
**Technology Area**: Recommender Systems
**Source URL**: https://netflixtechblog.com/fm-intent-predicting-user-session-intent-with-hierarchical-multi-task-learning-94c75e18f4b8
**Content Type**: article

### 1. Problem definition

#### 1.1. Origin

The system, named FM-Intent, is an enhancement to Netflix's existing recommendation foundation model (FM). While the base FM has been successful in understanding user preferences from interaction histories for next-item prediction, there is an opportunity to improve its capabilities by predicting the underlying user intent within a session. The core problem is to enrich the model's understanding of a user session beyond simple next-item prediction to provide a more comprehensive and nuanced recommendation experience.

#### 1.2. Relevance & reasons

Understanding user intent is crucial for delivering more accurate and personalized recommendations. By predicting not just *what* a user might watch next, but also *why* (i.e., their intent), the system can better connect members with relevant content. This drives significant product and business impact.

The project addresses limitations in existing intent prediction approaches, which often use simple multi-task learning that adds intent prediction heads to a next-item model without establishing a formal relationship between the tasks. FM-Intent introduces a hierarchical structure where intent prediction directly informs item recommendations.

#### 1.3. Expectations

The primary expectation is to create a more coherent and effective recommendation model that improves the accuracy of next-item predictions by first modeling a user's latent session intent. The system is expected to outperform existing state-of-the-art models, including Netflix's prior foundation model.

#### 1.4. Previous work

-   **Netflix Foundation Model (FM)**: The existing large-scale model for understanding user preferences from interaction histories, primarily focused on next-item prediction.
-   **FM-Intent-V0**: The production version of the Netflix model prior to FM-Intent. It performs well but lacks the ability to predict and leverage user intent.
-   **TransAct**: A Transformer-based model from Pinterest for real-time user action modeling, which is used as a state-of-the-art (SOTA) baseline for comparison.
-   **Academic Research**: The work is inspired by recent research highlighting the importance of user intent on online platforms.

#### 1.5. Usage volumes and patterns

The system has been integrated into the main Netflix recommendation ecosystem, implying it operates at a very large scale. However, for offline experiments, the FM-Intent model was trained on a "much smaller dataset" compared to the production FM model, due to the complexity of its hierarchical architecture.

### 2. Goals and anti-goals

#### 2.1. Goals

-   **Capture Latent Intent**: Model and predict a user's latent session intent using short-term and long-term implicit signals from their interaction history.
-   **Improve Next-Item Prediction**: Leverage the predicted user intent as an input to significantly improve the accuracy of next-item recommendations.
-   **Hierarchical Modeling**: Implement a hierarchical multi-task learning approach where intent prediction is a prerequisite for item prediction, ensuring the latter is informed by the former.
-   **Outperform Baselines**: Demonstrate statistically significant performance improvements over SOTA models, including the previous production model (`FM-Intent-V0`) and external benchmarks (`TransAct`).

#### 2.2. Anti-goals

-   **Simple Multi-Task Learning**: Avoid a simple multi-task architecture where intent prediction and next-item prediction are treated as parallel, independent tasks without a hierarchical dependency.

### 3. Risks and constraints

#### 3.1. Risks

[NO INFO]

#### 3.2. Constraints

-   **Computational Complexity**: The hierarchical prediction architecture of FM-Intent is complex, which constrained the training to a "much smaller dataset" than the one used for the main production foundation model.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

-   **Next-Item Prediction Accuracy**: The primary metric for evaluating the core recommendation task. Results are reported as relative percentage improvements over the `TransAct` baseline. FM-Intent achieved a 7.4% relative improvement.
-   **Next-Intent Prediction Accuracy**: The model is also evaluated on its ability to predict various intent proxies. The specific accuracy metrics are not defined, but results are reported as relative improvements for:
    -   Action Type
    -   Genre
    -   Movie/Show Type
    -   Time-since-release

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

The model is optimized using ground-truth labels for both intent and item IDs. The specific loss function (e.g., Cross-Entropy Loss) is not specified.

### 5. Data (Dataset)

#### 5.1. Data sources

The model is trained on "sampled Netflix user engagement data," which is an internal dataset composed of user interaction histories.

#### 5.2. Labeling strategy

The system predicts latent user intent, which is not directly observable. It uses several implicit signals derived from user interaction metadata as proxy labels for different dimensions of intent. These proxies serve as the ground-truth labels for the intent prediction tasks.

The defined intent proxies are:
-   **Action Type**: Categorizes the user's goal, such as discovering new content vs. continuing a series. An example is labeling a session as "continue watching" when a user plays a follow-up episode.
-   **Genre Preference**: The genre labels (e.g., Action, Thriller, Comedy) of the content a user interacts with during a session.
-   **Movie/Show Type**: Whether the user is engaging with a movie or a TV show.
-   **Time-since-release**: The age of the content being watched, categorized as newly released, recent (week to a month), or evergreen.

#### 5.3. Available metadata

The model uses "interaction metadata" from the user's session history. This includes a combination of categorical and numerical features representing user behavior. (see image: `Figure 1`).

#### 5.4. Data quality issues and cleaning/enrichment steps

[NO INFO]

#### 5.5. ETL or feature store architecture

[NO INFO]

### 6. Validation schema

#### 6.1. Train/validation/test split strategy

The article mentions "comprehensive offline experiments on sampled Netflix user engagement data." As a sequential recommendation problem focused on "next-item" and "next-intent" prediction, a time-based split is heavily `[inferred]`, where the model is trained on past interactions to predict future ones. However, the exact splitting methodology is not detailed.

#### 6.2. Cross-validation approach

[NO INFO]

#### 6.3. Holdout sets and update frequency

[NO INFO]

#### 6.4. Leakage risks and how they are mitigated

[NO INFO]

### 7. Baseline solution

The performance of FM-Intent was compared against several baseline models in offline experiments.

-   **SOTA Baseline**: `TransAct`, a Transformer-based model from Pinterest, was used as the primary SOTA baseline for reporting relative improvements.
-   **Internal Baseline**: `FM-Intent-V0`, the previous Netflix production model. For a fair comparison, it was trained on the same smaller dataset as FM-Intent.
-   **Standard Sequential Models**:
    -   `LSTM`
    -   `GRU`
    -   `Transformer`
-   **Modifications to Baselines**: For the `LSTM`, `GRU`, and `Transformer` baselines, additional fully-connected layers were added to enable them to predict user intent, as this was not part of their original implementations.

### 8. Errors and their analysis

#### 8.1. Error taxonomy

[NO INFO]

#### 8.2. Qualitative Analysis via User Clustering

Instead of a traditional error analysis, a qualitative analysis of the learned user intent embeddings was performed to validate their meaningfulness.

-   **Method**: K-means++ clustering (with K=10) was applied to the user intent embeddings generated by FM-Intent.
-   **Findings**: The analysis revealed distinct and meaningful user clusters that share similar intents and viewing patterns. (see image: `Figure 3`). Examples of identified clusters include:
    -   Users who primarily discover new content vs. those who continue watching recent/favorite content.
    -   Genre enthusiasts (e.g., anime or kids content viewers).
    -   Users with specific viewing patterns (e.g., "Rewatchers" vs. casual viewers).

This analysis suggests the model is learning a useful representation of user intent.

### 9. Training pipelines

#### 9.1. Tooling

[NO INFO]

#### 9.2. Preprocessing, training, evaluation, and deployment automation

The model architecture implies a specific, hierarchical training process (see image: `Figure 2`):
1.  **Input Feature Sequence Formation**: Rich input features are constructed for each interaction by combining categorical embeddings and numerical features from user interaction metadata.
2.  **User Intent Prediction**: The input sequence is processed by a Transformer encoder. The model then generates predictions for multiple intent signals (Action Type, Genre, etc.) via fully-connected layers. The individual intent predictions are aggregated using an attention mechanism to create a comprehensive `user intent embedding`.
3.  **Next-Item Prediction**: The final prediction task uses both the original input features and the generated `user intent embedding` as inputs to predict the next item.

The model is trained end-to-end using ground-truth labels for both intents and items to optimize predictions.

#### 9.3. Experiment tracking and CI/CD integration

The article mentions that the model was put "up and running in production," which implies the existence of experiment tracking and CI/CD pipelines, but no specific details are provided.

### 10. Features

#### 10.1. Feature categories

-   **Input Features**: A sequence of feature vectors, where each vector represents a user interaction. These are constructed by combining:
    -   Categorical embeddings from interaction metadata.
    -   Numerical features from interaction metadata.
-   **Engineered Features**:
    -   **User Intent Embedding**: This is a key feature generated by the model itself. It is an attention-based aggregation of the individual intent predictions. This embedding serves as a crucial input for the final next-item prediction task, capturing the relative importance of different intent signals for a given user.

#### 10.2. Feature store or batch/offline computation patterns

[NO INFO]

#### 10.3. Feature importance and ablation results

[NO INFO]

### 11. Measuring results

#### 11.1. Offline evaluation methodology

-   **Dataset**: Performed on a sampled subset of Netflix user engagement data.
-   **Comparison**: FM-Intent was benchmarked against a suite of baselines, including `TransAct` and `FM-Intent-V0`.
-   **Metrics**: Next-item prediction accuracy and next-intent prediction accuracy, reported as relative percentage improvements over the `TransAct` baseline.
-   **Key Result**: FM-Intent achieved a **7.4% statistically significant improvement** in next-item prediction accuracy compared to `TransAct`.

#### 11.2. A/B test design

The article confirms the system is in production but provides no details on the A/B testing framework, hypotheses, or online results.

#### 11.3. Reporting format and decision criteria

Offline results are presented in a table comparing the relative percentage improvements of FM-Intent and various baselines across next-item and multiple next-intent prediction tasks.

### 12. Integration and Serving

#### 12.1. API design, batch vs. online serving

[NO INFO]

#### 12.2. Infrastructure

-   **Model Core**: The architecture is based on a Transformer encoder with multi-head attention mechanisms.
-   **Deployment**: The model has been "successfully integrated into Netflix’s recommendation ecosystem."

#### 12.3. SLAs, latency budgets, and fallback strategies

[NO INFO]

#### 12.4. Release cycle for models vs. infrastructure

[NO INFO]

#### 12.5. Downstream Applications

The outputs of FM-Intent are leveraged in several downstream applications:
-   **Personalized UI Optimization**: The predicted intent can be used to customize the layout and content selection on the Netflix homepage (e.g., emphasizing different rows based on discovery vs. continue-watching intent).
-   **Analytics and User Understanding**: Intent embeddings and clusters provide insights into viewing patterns, which can inform content acquisition and production decisions.
-   **Enhanced Recommendation Signals**: The intent predictions serve as features for other recommendation models to improve their accuracy.
-   **Search Optimization**: Real-time intent predictions can be used to prioritize search results based on the user's current session intent.

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

[NO INFO]

### 14. Operations

#### 14.1. Day-to-day operational procedures

[NO INFO]

#### 14.2. Retraining cadence and ownership

[NO INFO]

#### 14.3. Incident response and rollback procedures

[NO INFO]

#### 14.4. Non-engineering considerations

[NO INFO]