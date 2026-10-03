**Company**: ManoMano
**Title**: Compatibility Challenges in Recommendation System
**Technology area**: Recommender System
**Source URL**: https://medium.com/manomano-tech/compatibility-challenges-in-recommendation-system-4d233c676d35
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The problem originates from the nature of ManoMano's e-commerce business, which specializes in DIY and home improvement products. Unlike sectors such as clothing or books, products in this domain often have strict compatibility requirements related to dimensions, voltage, or fittings. A common failure scenario is a customer purchasing a recommended mattress that does not fit the bed frame they also bought. This issue of product incompatibility in recommendations can lead to a frustrating customer experience, described as a "true nightmare."

#### 1.2. Relevance & reasons

Ensuring that recommended items work harmoniously together is crucial for customer trust and satisfaction. The system aims to improve an existing feature, the "Often Bought Together" widget, which suggests complementary products. Incompatible recommendations damage user trust and can lead to costly returns and negative reviews. The goal is to address this compatibility challenge systematically across the entire product catalog.

#### 1.3. Expectations

The primary expectation is that the recommendation system will suggest products that are compatible with each other. This involves:
*   Filtering out incompatible product suggestions from existing recommendation modules.
*   Generating compatible recommendations for new or rare products that lack user interaction data (cold-start problem).

#### 1.4. Previous work

The context for this work is an existing "Often Bought Together" widget. The initial version of this feature relied on user purchase history, which served as the first-pass solution.

#### 1.5. Usage volumes and patterns

[NO INFO]

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Improve Recommendation Quality**: Ensure that products recommended together are compatible, especially for items with specific technical requirements.
*   **Solve the Cold-Start Problem**: Generate compatible recommendations for new and rare products that have little to no user purchase history.
*   **Enhance Customer Satisfaction**: Reduce frustrating user experiences caused by incompatible product purchases.
*   **Automate Compatibility Rules**: Move from simple co-purchase heuristics to a more robust system that can generalize compatibility logic across the catalog.

#### 2.2. Anti-goals

*   **Avoid Sole Reliance on Co-purchase Data**: The system should not assume that all co-purchased items are compatible, as users can make random purchases (e.g., an adult bed and a baby mattress) that do not reflect true compatibility.
*   **Avoid Trivial Negative Training**: The model should not be trained on negative examples that are too easy or obvious to distinguish, as this does not lead to good performance on challenging real-world cases.

### 3. Risks and constraints

*   **Data Scarcity**:
    *   Manually labeled data for compatible/incompatible pairs is scarce due to the large volume of products in the catalog.
    *   Behavioral data (co-purchases) is unavailable for new or rare products, leading to the cold-start problem.
*   **Data Quality**:
    *   Purchase history is a noisy signal for compatibility, as it can include random, non-compatible co-purchases.
    *   The assumption that a lack of co-purchase indicates incompatibility is "not infallible."
    *   Product attribute data is unstructured and inconsistent. Issues include synonyms, different units of measurement (cm vs. mm), varied formatting (e.g., "140*190" vs. "length = 190 cm"), and language differences.
*   **Evaluation Difficulty**: There is a significant challenge in evaluating the model's real-world effectiveness. Offline binary classification metrics do not fully capture the impact on recommendation quality, and the team lacks reliable metrics to confirm the elimination of incompatible suggestions.
*   **Negative Sampling Complexity**: Constructing high-quality negative examples for training is difficult. They must be realistic and not "too obvious" for the model to learn meaningful distinctions.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Association Rule Metrics**: For the attribute-based approach, the key metrics used to find rules were:
    *   **Support**: Measures how frequently an itemset appears in the dataset.
    *   **Confidence**: Indicates the likelihood of item B being purchased when item A is purchased.
    *   **Lift**: Measures the strength of the association between items A and B compared to their independent probabilities.
*   **Binary Classification Metrics**: For the deep learning model, "various binary classification metrics" were assessed on a validation dataset. The specific metrics are not named.

#### 4.2. Online/business metrics

The article explicitly states that they "still lack reliable metrics that can confidently indicate whether we have successfully eliminated incompatible product suggestions." The high-level goal is to improve customer satisfaction.

#### 4.3. Loss functions

*   **ContrastiveLoss**: The primary loss function used for fine-tuning the sentence transformer model. It is designed to pull embeddings of compatible products closer together and push embeddings of non-compatible products farther apart. The mathematical definition is given as: `max(0, margin - distance(anchor, positive)) + max(0, distance(anchor, negative) - margin)`.
*   **Custom Weighted Loss**: The standard `ContrastiveLoss` was customized to incorporate the strength of the compatibility signal. The penalty for misclassifying a positive pair is weighted by the number of users who co-purchased the products, making the model more sensitive to misclassifying strongly-supported pairs.

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Customer Purchase History**: Transactional data showing which products were bought together in the same order.
*   **Product Catalog Data**: Textual information including product names, category names, attributes (e.g., dimensions), and descriptions.
*   **Expert Labels**: A small set of product pairs manually labeled as "compatible/non-compatible" by internal experts at ManoMano.
*   **Recommendation Interaction Data**: Logs of products that were suggested to users but were never clicked on.

#### 5.2. Labeling strategy

The problem was framed as a binary classification task.

*   **Positive Pairs (label=1, Compatible)**:
    *   Sourced from product pairs that were co-purchased at least N times.
    *   A higher value of N is used to increase confidence in the compatibility label.

*   **Negative Pairs (label=0, Non-compatible)**:
    *   **Initial approach (discarded)**: Randomly paired products from the entire catalog. This was found to be too easy for the model.
    *   **Improved approach**:
        1.  **Identify Complementary Categories**: Association Rules were used on historical co-orders to find pairs of categories that are frequently purchased together (e.g., beds and mattresses).
        2.  **Sample from Complementary Categories**: Random pairs of products were created from these identified complementary categories.
        3.  **Use Negative User Feedback**: Product pairs that were recommended to users but never clicked on (and never co-purchased) were also included as negative examples.

#### 5.3. Data quality issues and cleaning

*   **Attribute Normalization**: An attempt was made to extract and reformat product attributes, but this faced limitations due to variations in language, units, and formatting. This challenge was a key motivator for using an LLM that can process raw text.
*   **Text Concatenation**: For the deep learning model, all textual data for a product was concatenated into a single string with a `[sep]` separator: `Product Name [sep] Category Name [sep] Attribute1: Value1 Attribute2: Value2…`.

### 6. Validation schema

*   A validation dataset was constructed from the training data to assess the model using binary classification metrics.
*   The article acknowledges that this offline validation approach is insufficient and does not fully capture the model's real-world impact on recommendation quality.
*   No further details on the split strategy (e.g., time-based, cross-validation) are provided.

### 7. Baseline solution

Two simpler methods were used before adopting a deep learning approach:

1.  **Behavior-Based (Co-purchase)**: The first and most intuitive solution was to assume that if many customers bought two products together, they are likely compatible.
    *   **Drawbacks**: Suffers from the cold-start problem for new/rare products and is susceptible to noise from random, non-compatible purchases.

2.  **Attribute-Based (Association Rules)**: This method involved mining generalized compatibility rules from product attributes.
    *   **Method**: Association rules were applied to the attributes of co-purchased product pairs to find frequent patterns (e.g., "for a bed and mattress, `attribute:length` and `attribute:width` must have the same values").
    *   **Goal**: To generalize compatibility logic to the entire catalog, including cold-start products.
    *   **Drawbacks**: Limited by challenges in extracting and normalizing attributes from unstructured text.

### 8. Errors and their analysis

*   **Data Errors**:
    *   **False Positives**: Co-purchase data can incorrectly label non-compatible items as compatible (e.g., an adult bed and a baby mattress bought in the same order).
    *   **False Negatives**: The assumption that a lack of co-purchase implies incompatibility is not always correct.
*   **Feature Errors**:
    *   The association rules approach was hampered by the inability to reliably extract and match attributes due to inconsistencies in units (cm vs. mm), format ("140*190"), and language.
*   **Model Errors**:
    *   An initial model trained with randomly paired negative examples performed poorly because the task was too simple and did not reflect real-world ambiguity.
*   **Evaluation Gaps**: A key challenge identified is the gap between offline classification metrics and the actual user-perceived quality of recommendations. The team lacks a reliable way to measure if they have successfully eliminated incompatible suggestions in production.

### 9. Training pipelines

#### 9.1. Tooling

*   **Hugging Face Transformers**: The library was used for fine-tuning the sentence transformer model.
*   **Pre-trained Model**: `sentence-camembert-base`, a model pre-trained for sentence similarity tasks in French, was chosen as the starting point because the majority of products have French text.

#### 9.2. Training process

The fine-tuning process consists of the following steps:
1.  **Dataset Preparation**: Constructing a training set of product pairs with binary compatibility labels (1 for compatible, 0 for non-compatible).
2.  **Loss Function Definition**: Using a custom-weighted `ContrastiveLoss` to train the model.
3.  **Model Fine-tuning**: Fine-tuning the `sentence-camembert-base` model on the prepared dataset. The goal is to train the model to produce embeddings where the distance between compatible products is small and the distance between incompatible products is large.

#### 9.3. Experiment tracking and CI/CD

[NO INFO]

### 10. Features

#### 10.1. Feature categories

*   **Behavioral Features**:
    *   Co-purchase counts between product pairs.
*   **Product Textual Features**:
    *   Product Name
    *   Category Name
    *   Product Attributes (as key-value pairs)
    *   Product Description
*   **Product Image Features**: Mentioned as an ideal future input ("similar to how humans do!") but not used in the current implementation.

#### 10.2. Feature engineering

*   For the deep learning model, all textual features for a product are concatenated into a single input string: `Product Name [sep] Category Name [sep] Attribute1: Value1 Attribute2: Value2…`.
*   For the association rules baseline, there were attempts to extract and reformat attributes, but this proved difficult and had "certain limitations."

### 11. Measuring results

#### 11.1. Offline evaluation

*   A validation set was created from the training data.
*   The model was evaluated using "various binary classification metrics."
*   The team acknowledges that these offline metrics are insufficient for measuring the true impact on recommendation quality.

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting

[NO INFO]

### 12. Integration and Serving

The fine-tuned sentence transformer model is integrated into the recommendation system to provide compatibility scores for product pairs. It enhances the system in two main ways:

*   **Filtering Incompatible Recommendations**: The model is used as a filter. For a given recommendation, it calculates a compatibility score. Recommendations with a low score are filtered out, preventing incompatible suggestions from reaching the user. For example, a mattress of the incorrect size would receive a low score and be removed.
*   **Generating Recommendations for New/Rare Products**: To solve the cold-start problem, the model is used to find compatible candidates for products with no user history. The process involves:
    1.  Identifying complementary categories for the seed product.
    2.  Scoring products within those categories using the fine-tuned model.
    3.  Recommending the products with the highest compatibility scores.

#### 12.1. SLAs and Fallback

[NO INFO]

### 13. Monitoring

*   **Model Quality Monitoring**: This is identified as a major challenge. The team currently lacks reliable metrics to monitor in production whether the system is successfully eliminating incompatible product suggestions.
*   **Data Quality Monitoring**: [NO INFO]
*   **Engineering Metrics**: [NO INFO]

### 14. Operations

#### 14.1. Retraining and ownership

[NO INFO]

#### 14.2. Incident response and rollback

[NO INFO]

#### 14.3. Next steps

The article concludes by outlining several key areas for future improvement:
*   **Improve Evaluation**: Develop better methods and metrics for evaluating the effectiveness of the fine-tuned model in a real-world production environment.
*   **Refine Negative Sampling**: Improve the strategy for constructing negative examples for training to ensure they are both accurate and challenging enough to improve model performance.
*   **Explore Multimodal Models**: The article hints at a future direction of using both textual information and images to assess compatibility, similar to how humans do.