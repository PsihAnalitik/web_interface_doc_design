**Company**: Pinterest
**Title**: The machine learning behind delivering relevant ads
**Technology Area**: Predictive ML
**Source URL**: https://medium.com/pinterest-engineering/the-machine-learning-behind-delivering-relevant-ads-8987fc5ba1c0
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The system is designed to support Pinterest's advertising platform. The core problem is to help advertisers find and reach new, relevant users who are similar to their existing customers. This feature is known as Actalike (AAL) audiences, or Lookalike audiences in the wider industry. The goal is to expand an advertiser's audience to potentially new users who are likely to be interested in their products or brand.

#### 1.2. Relevance & reasons

Pinterest aims to ensure that ads are additive and not intrusive for its users. By delivering more relevant ads, the platform can improve the user experience while also providing value to advertisers. AAL audiences are a key feature for advertisers to achieve relevance by leveraging Pinterest's first-party signals about user interests, intent, and engagement. High-quality audience expansion can lead to improved advertiser outcomes (e.g., revenue) and better user engagement with ads.

#### 1.3. Expectations

The system is expected to produce high-quality audience expansions that outperform previous methods. This quality is measured through both offline ranking metrics (precision, recall) and online business metrics (revenue, impressions, engagement quality). The system should be scalable and efficient, simplifying the complexity of previous solutions.

#### 1.4. Previous work

The previous production version of the AAL system was a hybrid solution. It blended the results from two different models:
1.  A regression-based classifier model.
2.  A similarity-based model.

This hybrid approach was complex, leading to higher infrastructure and maintenance costs. The new system aims to replace this with a single, more powerful model.

#### 1.5. Usage volumes and patterns

The system operates at a large scale:
*   **Seed Lists**: O(10⁵) advertiser seed lists.
*   **Users**: O(10⁸) monthly active users (MAUs) to score against each seed list.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Improve Audience Quality**: Generate higher-quality AAL audience expansions, measured by offline recall/precision and online engagement metrics.
*   **Improve Business Metrics**: Increase key advertiser metrics such as revenue, impressions, and eCPM for AAL campaigns.
*   **Improve User Engagement**: Increase positive engagement signals (Good Click Ratio) and decrease negative signals (Hide Rate).
*   **Simplify System Architecture**: Replace the complex hybrid model system with a single, unified model to reduce infrastructure and maintenance costs.
*   **Improve Efficiency**: Speed up the end-to-end runtime for training and scoring. The new system achieved a >20% runtime improvement.

#### 2.2. Anti-goals

*   **Maximizing Raw CTR at All Costs**: The system is not optimized solely for click-through rate (CTR). In online experiments, CTR dropped by 5.7%, but this was accompanied by an 8.3% drop in hide rate and a 2.7% gain in good click ratio, indicating an overall improvement in the quality of engagement.

### 3. Risks and constraints

#### 3.1. Technical Risks

*   **Data Sparsity / Overfitting**: For advertisers with small seed lists (e.g., several thousands of users), models can easily overfit. The system must perform well even with small seed lists.
*   **Scalability**: The model must perform well on very large seed lists (e.g., tens of millions of users) without being computationally prohibitive.
*   **Model Convergence**: With sparse inputs, neural network models may not converge well. This was a motivation for using dense user embeddings as input.

#### 3.2. Technical Constraints

*   **Computational Scale**: The system must regularly train models for O(10⁵) seed lists and score O(10⁸) users for each, requiring a scalable infrastructure (Spark, Kubernetes).
*   **Runtime**: The end-to-end process of generating audience expansions has a runtime constraint. The new system was required to be at least as fast as the previous one and ultimately improved runtime by over 20%.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

Offline evaluation treats audience expansion as a ranking problem. The quality is measured by how well the model ranks a holdout set of users.

*   **recall@k**: Measures the fraction of holdout users that appear in the top-k expanded user list.
    *   Definition: `recall@k = |E@k ∩ H| / |H|`
    *   `E@k`: The set of top-k users in the expansion list.
    *   `H`: The holdout set of users from the seed list.
*   **precision@k**: Measures how much better the expansion is than a random selection of users.
    *   Definition: `precision@k = (|E@k ∩ H|) / (|E@k ∩ R|)`
    *   `R`: A randomly selected set of users from MAUs with the same size as `H`.

Metrics are averaged over multiple values of `k` to evaluate performance across different target expansion sizes.

#### 4.2. Online/business metrics

Metrics were measured in a two-week online A/B test for the AAL ads slice.
*   **Revenue**: +3.1%
*   **Impressions**: +3.6%
*   **eCPM (effective cost per mille)**: +0.44% (from sample weighting experiment)
*   **Users with ads impressions**: Statistically significant gain.
*   **Users with revenue**: Statistically significant gain.
*   **CTR (Click-Through Rate)**: -5.7%
*   **HDR (Hide Rate)**: -8.3%
*   **GCR (Good Click Ratio)**: +2.7%

#### 4.3. Loss functions

The model is trained by optimizing a **weighted binary cross-entropy loss function**.

*   **Formula**:
    `Loss = -1/N * Σ(i=1 to N) [y_i * log(p_i) * (1 + Σ(j=1 to M) w_ij) + (1 - y_i) * log(1 - p_i)]`
    *   `N`: Number of samples.
    *   `y_i`: Ground truth label (1 for seed user, 0 for negative sample).
    *   `p_i`: Predicted probability of being in the seed list.
    *   `M`: Number of different engagement metrics used for weighting.
    *   `w_ij`: Sample weight for sample `i` based on engagement metric `j`.

The weighting `(1 + Σ w_ij)` is applied only to positive examples (`y_i=1`), favoring seed users with higher historical engagement.

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Positive Examples**: An advertiser's "seed list" of users.
*   **Negative Examples**: Randomly sampled Monthly Active Users (MAUs) from the advertiser's targeting country.
*   **User Embeddings**: Pre-trained universal user embeddings derived from organic `<user, pin>` interactions on the Pinterest platform.
*   **Engagement Metrics**: Historical user engagement data used for sample weighting, such as number of impressions and CTR.

#### 5.2. Labeling strategy

The problem is framed as binary classification:
*   **Positive Label (1)**: Users belonging to the advertiser's seed list.
*   **Negative Label (0)**: Users sampled from the general MAU population.

#### 5.3. Data quality and cleaning

*   **Sample Weighting**: To account for varying levels of user value within a seed list, positive examples are weighted based on engagement metrics.
    *   Metrics like CTR (< 1) are upscaled by 10⁶.
    *   A log transformation is applied to metrics > 1 to ensure they are normally distributed.
    *   Min-max scaling is used to normalize all sample weights to be within the range [0, 1].
*   **Sampling for Large Seed Lists**: For large seed lists (e.g., millions of users), only up to 200,000 positive samples are used for training the neural network model.

### 6. Validation schema

#### 6.1. Train/validation/test split

A specific holdout strategy is used for offline evaluation of each seed list:
1.  **Split**: A given seed list is split into a 90% training set and a 10% holdout set.
2.  **Training**: A model is trained using the 90% portion as positive examples.
3.  **Scoring**: The trained model scores all MAUs, excluding the 90% training set.
4.  **Evaluation**: The rank of the 10% holdout users within the scored list is examined using `recall@k` and `precision@k`.

This process is repeated across multiple seed lists of varying sizes (from thousands to tens of millions) to ensure the model generalizes well.

#### 6.2. Leakage risks

[NO INFO]

### 7. Baseline solution

The proposed model was compared against two baseline approaches and the previous production system.

*   **Regression-based model**: A logistic regression model trained for each seed list using raw user features. This approach performs well on large seed lists but poorly on small ones.
*   **Similarity-based model**: An approach based on Locality Sensitive Hashing (LSH) and pre-trained user embeddings. It expands audiences based on nearest neighbors (e.g., via cosine similarity). This approach performs well on small seed lists but is outperformed on large ones.
*   **Hybrid Production System (A/B Test Control)**: The previous system which blended the expansion lists from both the regression-based and similarity-based models.

The proposed combined NN model outperformed all baselines in both offline and online evaluations.

### 8. Errors and their analysis

The analysis focused on model performance across different seed list sizes.

*   **Small Seed Lists (e.g., thousands)**:
    *   **Regression-based models** perform poorly, likely due to overfitting on sparse, raw features.
    *   **Similarity-based and Combined NN models** perform well, as they leverage dense, pre-trained universal user embeddings, which reduces variance and prevents overfitting.
*   **Large Seed Lists (e.g., millions)**:
    *   **Similarity-based models** are outperformed by supervised approaches.
    *   **Combined NN model** surprisingly outperforms the **regression-based model**, even though the NN model was trained on a subset of positive samples (up to 200k) while the regression model used all of them. This is attributed to two factors:
        1.  The dense user embeddings allow the model to converge faster.
        2.  The MLP layers can capture non-linear relationships in the data that the logistic regression model cannot.

### 9. Training pipelines

#### 9.1. Tooling

*   **Spark**: Used for large-scale data processing, model training, and scoring users against each seed list.
*   **Kubernetes**: Used for orchestrating the training and scoring jobs.

#### 9.2. Automation

*   The system is designed to support "regularly trained models for seed lists," indicating an automated pipeline for model creation and refresh.
*   The end-to-end system was productionized to handle the entire workflow from training to scoring, simplifying the previous hybrid system. This simplification led to a >20% improvement in end-to-end runtime.

### 10. Features

#### 10.1. Feature categories

*   **Primary Input Feature**: Pre-trained universal user embeddings. These are dense representations that encode high-level information about user behavior.
*   **Feature Source**: The embeddings are trained on organic `<user, pin>` interactions on the Pinterest platform.
*   **Feature Transformation**: The user embeddings are normalized before being fed into the per-advertiser MLP models.

#### 10.2. Feature selection

The core design choice was to use pre-trained user embeddings instead of raw, sparse features. This was done to combine the strengths of similarity-based approaches (low variance, solving data sparsity) and regression-based approaches (supervised learning, encoding seed list structure). The embeddings allow the downstream MLP classifiers to converge faster and capture complex patterns.

### 11. Measuring results

#### 11.1. Offline evaluation

*   The proposed "Combined NN" model was compared against the "Regression-based" and "Similarity-based" baselines using the 90/10 holdout validation schema.
*   Results showed that the Combined NN approach consistently outperformed both baselines across all seed list sizes in terms of both `recall@k` and `precision@k`.

#### 11.2. A/B test design

*   **Control Group**: The previous production system, which was a hybrid solution blending classifier and similarity-based models.
*   **Treatment Group**: The new system using the single combined model (user embeddings + MLP classifier).
*   **Duration**: Two weeks.
*   **Hypothesis**: The new model would generate higher-quality audiences, leading to improved reach and revenue.
*   **Decision**: The new model was launched based on statistically significant gains in revenue (+3.1%), impressions (+3.6%), and engagement quality (GCR, HDR), despite a drop in CTR. The results were seen as consistent with the offline evaluation's finding of improved recall, which translated to better user reach online.

### 12. Integration and Serving

#### 12.1. API design

[NO INFO]

#### 12.2. Serving architecture

*   **Architecture Type**: The system is a batch processing pipeline. [inferred] It regularly trains models and scores all eligible users (O(10⁸)) against each seed list (O(10⁵)) to generate expansion lists.
*   **Infrastructure**: The pipeline is built on **Spark** for distributed computation and orchestrated by **Kubernetes**.
*   **Model Architecture**: The core model is a multi-layer perceptron (MLP) binary classifier built for each advertiser seed list. It takes normalized user embeddings as input.
*   **Simplification**: The production architecture was "drastically simplified" by replacing the previous hybrid system with this single, unified model, saving infrastructure and maintenance costs.

#### 12.3. SLAs and fallback

*   **Latency**: The end-to-end runtime of the batch pipeline was improved by over 20%. No online serving latency is discussed.
*   **Fallback**: [NO INFO]

### 13. Monitoring

#### 13.1. Data quality monitoring

[NO INFO]

#### 13.2. Model quality monitoring

*   **Prediction Drift**: [NO INFO]
*   **Business Metrics**: Key online A/B test metrics are tracked to measure the business impact of model changes. These include:
    *   Revenue
    *   Impressions
    *   eCPM
    *   CTR
    *   Hide Rate (HDR)
    *   Good Click Ratio (GCR)

These metrics are presumably monitored post-launch to ensure continued performance. [inferred]

#### 13.3. Engineering metrics

*   **Runtime**: The end-to-end system runtime is a key metric, which was improved by >20%.
*   **Cost**: Infrastructure and maintenance costs are tracked, and the new system resulted in savings.

### 14. Operations

#### 14.1. Retraining cadence

Models are "regularly trained for seed lists," but the specific frequency (e.g., daily, weekly) is not mentioned.

#### 14.2. Incident response

[NO INFO]

#### 14.3. Future work

The team plans to explore more advanced modeling structures to further improve audience expansion quality, including:
*   Deep Factorization Machine (DFM)
*   Contextual AAL models