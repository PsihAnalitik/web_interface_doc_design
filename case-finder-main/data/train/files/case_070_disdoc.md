**Company**: Foodpanda
**Title**: Classifying restaurant cuisines with subjective labels
**Technology area**: Predictive ML
**Source URL**: https://medium.com/foodpanda-data/classifying-restaurant-cuisines-with-subjective-labels-fa10012d18a9
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The core business problem is to accurately and automatically tag restaurants on the Foodpanda platform with appropriate cuisine labels. These labels are critical for downstream features that enhance customer search and discovery. Cuisine categories can be dish-based (e.g., Chicken, Pasta) or geographical/cultural (e.g., Italian, Singaporean).

The problem's complexity stems from the subjective nature of cuisine definitions, which can vary by region and individual perception (e.g., whether Chendol is Singaporean or Malaysian).

#### 1.2. Relevance & reasons

A manual labeling approach was attempted but proved to be ineffective for several reasons:
*   **Scalability**: It is too time-consuming to manually tag hundreds of thousands of restaurants across the 11 markets Foodpanda operates in.
*   **Consistency**: Manual labeling resulted in inconsistencies, where two restaurants with similar menus were tagged differently by different labelers due to a lack of alignment on cuisine definitions.
*   **Completeness**: Given the large number of possible cuisines, labelers often missed applying all relevant tags to a restaurant.
*   **Multi-label complexity**: Many vendors serve a multi-cultural mix of cuisines, making manual tagging even more difficult.

An automated solution was required to standardize labels at scale and improve the customer experience.

#### 1.3. Expectations

The primary expectation is an automated solution that produces standardized cuisine labels. These labels should ultimately improve the customer's search and discovery experience, helping them find desired food "more quickly and accurately." The solution should be scalable and produce results accurate enough for production use.

#### 1.4. Previous work

The main previous approach was **manual labeling**. This was deemed unscalable and produced inconsistent, incomplete data. The article also mentions that other models were considered and evaluated (summarized in a table that is not included in the source text), implying that purely supervised or rule-based models were likely explored but found to be less suitable in terms of effort and scalability.

#### 1.5. Usage volumes and patterns

The system needs to operate across Foodpanda's entire platform, which includes "hundreds of thousands of restaurants" across 11 markets.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Automation**: Develop an automated system to assign cuisine tags to restaurants.
*   **Scalability**: The solution must be scalable to hundreds of thousands of restaurants across multiple markets.
*   **Accuracy & Relevance**: The generated tags should be "reasonably accurate" and reflect local customer opinions and search behaviors to improve the user experience.
*   **Stakeholder Buy-in**: The approach should be transparent enough (a 'white-box' approach) to gain trust and approval from business stakeholders.
*   **Efficiency**: Reduce the manual effort required compared to a fully supervised or rule-based model.

#### 2.2. Anti-goals

*   **Perfect Subjectivity Resolution**: The system does not aim to definitively solve philosophical debates about cuisine origins (like the Chendol example), but rather to use labels that are most useful to customers in a given local context.
*   **Complete Automation**: The system is not expected to be fully autonomous. It incorporates a human-in-the-loop validation step to ensure quality.
*   **Initial Perfection**: The goal is not a perfect model from the start, but one that is "reasonably accurate" and can be iterated upon. The initial model has known limitations, such as handling fusion cuisines.

### 3. Risks and constraints

*   **Data Subjectivity**: The core definition of "cuisine" is subjective, leading to inconsistent ground truth and difficulty in evaluation.
*   **Proxy Label Noise**: The method of using customer clicks as a source for "correct" labels is imperfect. Customer clicks may not always accurately reflect the cuisine of a restaurant.
*   **Feature Ambiguity**: The similarity approach based on menu item names can lead to false positives. The example given is "Carrot Cake," which can refer to a Singaporean savory dish or a Western dessert, leading to incorrect similarity matches.
*   **Pre-defined Cuisine List**: The model is limited to a pre-defined list of cuisines and cannot discover entirely new ones on its own in its current form.
*   **Fusion Cuisines**: The model struggles to identify a fusion of cuisines, performing better on restaurants with a single, dominant cuisine type.
*   **Error Detection Limitation**: The current approach is designed to identify missing cuisine tags or affirm existing ones, but not to identify and remove *incorrect* existing tags.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The article does not specify any quantitative offline metrics (e.g., precision, recall, F1-score). The primary evaluation method is a qualitative manual validation process performed by "labelling specialists." The model's output is considered successful if the results are "reasonably accurate to roll out on production confidently."

#### 4.2. Online/business metrics

The ultimate goal is to "improve customer’s search and discovery experience" and help them "find what they are looking for more quickly and accurately." Specific online A/B testing metrics are not mentioned.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Restaurant Menus**: The names of all menu items for all restaurants on the platform.
*   **Customer Behavior Data**:
    *   Search keywords entered by users.
    *   Restaurant profiles that customers click on after performing a search.
*   **Manual Labels**: Initial, inconsistently-labeled data from a previous manual tagging exercise.

#### 5.2. Labeling strategy

A semi-supervised approach is used to generate and propagate labels:

1.  **Proxy Label Generation (Seed Set Creation)**:
    *   A list of high-confidence keywords is established for specific cuisines.
    *   The system analyzes customer clicks on restaurants following searches for these keywords.
    *   Restaurants that are frequently clicked for a cuisine-specific keyword are assumed to belong to that cuisine, forming a set of "correctly" labeled seed restaurants.

2.  **Label Propagation via Similarity**:
    *   The labels from the seed set are propagated to all other unlabeled restaurants based on menu similarity.

#### 5.3. Data quality issues

*   **Inconsistent Manual Labels**: The initial hand-labeled data suffered from inconsistency and missing labels due to subjective definitions and human error.
*   **Ambiguous Item Names**: Menu item names can be identical across different cuisines but refer to different dishes (e.g., "Carrot Cake").

### 6. Validation schema

The validation process is a manual, human-in-the-loop step performed after model prediction:

*   **Human Validation**: "Labelling specialists" manually validate the cuisine labels generated by the model.
*   **Guided Task**: Instead of having to consider all possible cuisines for a restaurant, the specialists are provided with a narrowed-down list of model-predicted cuisines.
*   **Validation Goal**: The specialists' task is to confirm correct predictions and "sieve out wrong cuisines" (false positives). They fill out a form to record their validation decisions.
*   **Reduced Subjectivity**: This process is considered less subjective than initial manual labeling because the specialists are confirming or rejecting a small set of suggestions rather than generating labels from scratch.

There is no mention of traditional train/validation/test splits.

### 7. Baseline solution

The primary baseline was **manual labeling**. This was performed on a sample of restaurants but was found to be:
*   Too time-consuming and not scalable.
*   Prone to inconsistencies due to subjective definitions.
*   Likely to miss some relevant cuisine tags for a given restaurant.

The article also alludes to considering and weighing other approaches like supervised or rule-based models, but found the chosen semi-supervised method to be more scalable with lower upfront effort.

### 8. Errors and their analysis

The model has several known error modes and limitations:

*   **False Positives**: The model can incorrectly assign a cuisine tag. This is often caused by ambiguity in menu item names that leads to high similarity scores between restaurants of different cuisines.
    *   **Example**: A restaurant selling a Western-style "Carrot Cake" might be incorrectly tagged with the same cuisine as a hawker stall selling the Singaporean savory "Carrot Cake" dish.
*   **False Negatives (Missed Cuisines)**: The model is not effective at identifying a "fusion of cuisines." It tends to identify the dominant cuisine type but may miss other, less prominent ones.
*   **Source of Error (Proxy Labels)**: The initial seed labels, derived from customer clicks, may not always be correct.
*   **Source of Error (Embeddings)**: The restaurant embedding, calculated as an average of its menu item embeddings, is a simple representation that can be skewed or fail to capture nuance.

### 9. Training pipelines

The system is built as a multi-step pipeline:

1.  **Proxy Label Generation**:
    *   Identify high-confidence cuisine keywords.
    *   Analyze customer search and click data to assign cuisine labels to a seed set of restaurants.
2.  **Embedding Generation**:
    *   Use `fastText` to generate vector embeddings for every menu item across all restaurants.
    *   For each restaurant, calculate a single restaurant-level embedding by averaging the embeddings of all its menu items.
3.  **Similarity Calculation**:
    *   Calculate the cosine similarity score between the embedding of each seed restaurant and the embeddings of all other restaurants.
4.  **Prediction Generation**:
    *   For an unlabelled restaurant, if it has a high cosine similarity score with a seed restaurant, the cuisine label from that seed restaurant is propagated to it.
5.  **Manual Validation**:
    *   The generated predictions are passed to labeling specialists for final validation.

### 10. Features

#### 10.1. Feature categories

*   **Text Features**:
    *   Restaurant menu item names.
    *   Customer search keywords.
*   **Behavioral Features**:
    *   Customer clickstream data (linking search keywords to restaurant clicks).

#### 10.2. Feature engineering

*   **Item Embeddings**: `fastText` embeddings are generated for each menu item name.
*   **Restaurant Embeddings**: A restaurant-level feature vector is created by taking the average of all its menu item embeddings. This aggregated embedding is used for similarity comparisons.

### 11. Measuring results

#### 11.1. Offline evaluation

Evaluation is primarily qualitative. The generated labels are manually reviewed by "labelling specialists" who confirm or reject the suggestions. The key success criterion is whether the results are "reasonably accurate" enough to be used in production. Stakeholder buy-in, achieved through the transparent, customer-behavior-driven approach, was also a key measure of success.

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting

The output of the validation step is a form filled in by the labeling specialists. The overall project's success was communicated by highlighting the 'white-box' nature of the approach, which links predictions back to observable customer behavior.

### 12. Integration and Serving

#### 12.1. API design

The system's output is a set of cuisine tags for each restaurant. The article states these tags are "to be used for various features on the platform to improve customers’ search and discovery experience." This implies a batch prediction process where the tags are generated offline and stored in a database to be consumed by other services, rather than a real-time prediction API. `[inferred]`

#### 12.2. Infrastructure

[NO INFO]

#### 12.3. SLAs, latency budgets, and fallback strategies

[NO INFO]

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Day-to-day operational procedures

The primary operational task described is the **manual validation** of model-generated labels by a team of "labelling specialists." This human-in-the-loop process is integral to maintaining the quality of the cuisine tags.

#### 14.2. Retraining cadence

[NO INFO] However, the model's reliance on customer behavior data implies that it would need to be periodically re-run to stay current.

#### 14.3. Incident response and rollback procedures

[NO INFO]

#### 14.4. Future improvements and expansions

The team has identified several areas for future work:
*   **Threshold Tuning**: Find the optimal cosine similarity score threshold for propagating labels.
*   **New Category Discovery**: Identify new, more granular cuisine categories (e.g., splitting "Beverages" into "Coffee," "Bubble Tea") by observing clusters in the embedding space.
*   **Incorrect Tag Identification**: Experiment with using similarity scores to identify and flag existing tags that are incorrect (e.g., if a tagged restaurant has a very low similarity score with other restaurants of the same cuisine).
*   **Internationalization**: Expand the model to support other languages, including character-based languages like Chinese and Thai.