- Company: Nextdoor
- Title: Using predictive technology to foster constructive conversations
- Technology area: NLP, Content Moderation
- Source URL: https://engblog.nextdoor.com/using-predictive-technology-to-foster-constructive-conversations-4af437942bd4
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The system is designed to support Nextdoor's purpose of cultivating a kinder online environment. The core problem is that online conversations can become uncivil, contentious, or abusive. Analysis of platform data shows that unkind comments often lead to more unkind comments, creating negative feedback loops. Specifically, 90% of abusive comments appear in a thread with another abusive comment, and 50% appear in threads with 13 or more other abusive comments.

The goal is to move from a reactive moderation model to a proactive one by anticipating when a conversation thread is likely to become heated *before* a user contributes, allowing for timely intervention.

#### 1.2. Relevance & reasons

The primary motivation is to prevent negative feedback loops in conversations. By identifying potentially contentious threads early, Nextdoor can deploy "strategic nudges" to encourage more mindful and constructive conversations. This is expected to improve the overall health of the platform and user experience. The system enables several product interventions aimed at reducing uncivil content.

#### 1.3. Expectations

The system is expected to predict whether a future comment on a thread will be abusive or contentious. This predictive signal is then used to power various intervention tools, such as the "Constructive Conversations Reminder," which prompts users to be more empathetic when commenting on a potentially heated thread.

#### 1.4. Previous work

Nextdoor previously implemented several mechanisms to encourage kindness:
*   **Kindness Reminder (2019):** Automatically detects offensive language in a comment as it is being written and encourages the author to edit it before publishing.
*   **Anti-Racism Notification (2021):** A specific application of the Kindness Reminder that detects racist language.

These prior systems were reactive, analyzing the content of a single comment being composed. The new "thread model" is proactive, analyzing the state of an entire conversation thread to predict future negative interactions.

#### 1.5. Usage volumes and patterns

*   The system was initially developed and validated using data from the U.S., primarily from Q3 2021.
*   The platform has a global user base, and a key requirement is for the model to be effective in other countries and languages.
*   Less than 1% of comments on the platform get reported.

### 2. Goals and anti-goals

#### 2.1. Goals

*   Proactively identify conversation threads that are at risk of becoming contentious or abusive.
*   Provide a predictive signal to power product interventions like:
    *   Suppressing notifications for triggering comments.
    *   Displaying a "Constructive Conversations Reminder."
    *   Prompting the original post author to close the discussion.
*   Develop a model that can be internationalized to support Nextdoor's global user base, even in markets with sparse training data.
*   Achieve high enough performance (AUC, precision, recall) to be useful for product interventions.

#### 2.2. Anti-goals

*   **Optimizing for lowest latency:** The team explicitly chose a higher-latency model (BERT) over a lower-latency one (Fasttext) because its multilingual capabilities and performance were more important. The system architecture was designed to accommodate this higher latency, indicating that minimizing inference time was not the primary goal.

### 3. Risks and constraints

*   **Data Imbalance:** The positive class (reported comments) is rare, constituting less than 1% of all comments.
*   **Data Clustering:** Reported comments tend to cluster within a small number of large, trending threads, which complicates representative data sampling.
*   **Label Noise/Incompleteness:** The label is based on user reports. Not all abusive content gets reported, which can lead to a high rate of apparent false positives (the model flags a thread that contains uncivil content that was never reported). Human review confirmed that many of these "false positives" were indeed contentious.
*   **Complex Data Structure:** Conversations on Nextdoor are multi-dimensional, involving posts, sequential comments, direct replies, and user mentions/tags. Modeling this structure correctly is a key challenge.
*   **Internationalization Performance:** There is a risk that a model trained primarily on U.S. data will not perform well in other countries due to cultural and linguistic differences. Initial tests showed this was a valid concern, though performance was still sufficient in most tested markets. Performance in non-western cultures and languages remains an unknown.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **AUC:** The primary offline metric used for model evaluation. The model achieved an AUC of over 0.83.
*   **Precision and Recall:** The model was able to achieve "double digit precision and recall at certain thresholds."
*   **International Validation:** AUC was used to compare the performance of the U.S.-trained model on data from various European countries.

#### 4.2. Online/business metrics

*   The effectiveness of the interventions powered by the model (e.g., reduction in uncivil content after rolling out the "Constructive Conversations Reminder"). The article notes that the feature rollouts demonstrated the model "can perform quite well."

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The data is sourced from Nextdoor's internal platform data, including:
*   Posts and their associated comment threads.
*   Comment text.
*   The relationship between comments (sequential order, reply-to hierarchy, user mentions/tags).
*   User-generated reports on content.

#### 5.2. Labeling strategy

The task is framed as predicting if a future comment in a thread will be reported.
*   **Positive Label:** A thread is considered positive if a subsequent comment within it is reported by a user.
*   **Rationale:** Using "reporting" rather than "removal" was a deliberate choice to capture early signals of a conversation becoming contentious, regardless of the final moderation decision. A report indicates that the conversation has reached a level of friction that warrants intervention.

#### 5.3. Data quality issues and cleaning

*   **Imbalance:** Less than 1% of comments receive a report.
*   **Clustering:** Reported comments are not independent and tend to cluster in popular threads.
*   **Sampling Strategy:** To address these issues, a two-step sampling process was used to create a balanced and representative training set:
    1.  Sample by post.
    2.  Within each sampled post's thread, sample both positive (reported) and negative (not reported) comments.

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

#### 6.1. Train/validation/test split

*   The training data was sampled from "across multiple months."
*   The article mentions "offline validation" but does not specify the exact split strategy (e.g., chronological split).
*   For internationalization, the U.S.-trained model was evaluated on holdout datasets from multiple European countries (e.g., Netherlands).

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets

*   Data from various European countries was used as a holdout set to test the generalizability of the U.S.-trained model.
*   Online A/B testing was used to compare the performance of multilingual vs. English-only embeddings in the U.S. market.

### 7. Baseline solution

The article does not describe a simple baseline model for the specific task of predicting future thread contention. Instead, it contrasts the new proactive approach with previous reactive systems that analyzed single comments for offensive language. The choice between Fasttext and BERT embeddings was evaluated, but this was a component-level decision rather than a full system baseline.

### 8. Errors and their analysis

*   **Primary Error Type: False Positives:** The model identifies a thread as high-risk for contention, but no subsequent comment in the thread gets reported.
*   **Error Analysis:**
    *   A human review of a random sample of these "false positives" revealed that the comments in these threads were often as contentious as those in true positive threads.
    *   This suggests the error is often due to noisy or incomplete labels (i.e., under-reporting of abusive content by users) rather than a model failure.
    *   The low incidence rate of reporting inherently limits the model's maximum achievable precision.
*   **International Performance:** A slight drop in precision and recall was observed in European markets compared to the U.S., potentially due to lower reporting rates in those regions.

### 9. Training pipelines

#### 9.1. Tooling

*   **Embeddings:** The `sBert` API was used to generate text embeddings.
*   **Model Framework:** The classifier is a "simple dense neural layer," implying the use of a standard deep learning framework like TensorFlow or PyTorch.

#### 9.2. Preprocessing, training, and evaluation

*   **Thread Reconstruction:** The most predictive representation of a conversation was found by considering all relationships: mentions/tags, reply-to hierarchy, and sequential comment order. Text from this reconstructed thread is used as input.
*   **Feature Generation:** Text embeddings are generated from the thread content using a BERT model.
*   **Training:** The model consists of a dense neural layer built on top of concatenated embeddings from the thread. The team experimented with various fine-tuning approaches for the embeddings.

### 10. Features

#### 10.1. Feature categories

1.  **Text Embeddings (Primary):** Vector representations of the comment text within a thread. This was identified as the most important feature group, responsible for most of the AUC gains.
2.  **Behavioral Features (Secondary):**
    *   Number of reports on a neighbor’s previous content.
    *   Comment creation velocity in the thread.
    These features were noted to "add signal" and were planned for inclusion in future model iterations.

#### 10.2. Feature selection

*   The core of the model is built on text embeddings derived from the thread structure.
*   A key decision was selecting the embedding technology. BERT was chosen over Fasttext despite its higher latency due to its superior performance and, crucially, its support for pre-trained multilingual aligned embeddings. This allows a model trained on U.S. data to perform well in other languages.

### 11. Measuring results

#### 11.1. Offline evaluation

*   The final model achieved an AUC > 0.83 on offline test data.
*   It achieved "double digit precision and recall at certain thresholds."
*   For internationalization, the U.S.-trained model's AUC was compared across several European countries. In most cases, the AUC was close to U.S. levels, validating the multilingual approach.

#### 11.2. A/B test design

*   Online A/B testing was conducted in the U.S. to confirm that the multilingual-aligned BERT embeddings performed as well as English-only embeddings for the task.
*   Product interventions powered by the model, like the "Constructive Conversations Reminder," were rolled out to users, implying they were validated via A/B testing before full launch.

### 12. Integration and Serving

#### 12.1. API design

The model provides a predictive signal (likely a contention score) for a given conversation thread. This signal is consumed by various downstream product tools to trigger interventions. The architecture supports asynchronous processing.

#### 12.2. Infrastructure

The serving architecture is designed to mitigate the high latency of the BERT model:
*   **Asynchronous Processing:** Downstream tasks dependent on the embeddings can run asynchronously.
*   **Pre-computation:** Embedding features are pre-generated and stored.
*   **Caching:** Scores are cached to be consumed later by product surfaces.

This design allows the system to use a powerful but slow model for a task that is not in a user-blocking, real-time request path.

#### 12.3. SLAs, latency budgets, and fallback strategies

The asynchronous architecture implies that the system does not have a strict, low-latency SLA. The trade-off was explicitly made in favor of model quality and multilingual capabilities over low latency.

#### 12.4. Release cycle

The model was developed, validated, and rolled out in the U.S. first. After confirming its performance, it was evaluated on international data before being used to power features globally.

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Retraining cadence

[NO INFO]

#### 14.2. Ownership

The project was a cross-functional effort involving:
*   Individual contributors (Sugin Lou, Karthik Jayasurya).
*   The CoreML team.
*   The Moderation Team engineers.
*   External guidance from the Neighborhood Vitality Advisory Board (academics and experts in social psychology, equality, and civic engagement).

#### 14.3. Incident response and rollback procedures

The model's output is used to power several interventions, which can be individually enabled or disabled:
*   **Comment notification suppression:** Rolled out.
*   **Constructive Conversations Reminder:** Began rolling out in the U.S.
*   **Prompt author to close discussion:** A potential future intervention.

This modular approach allows for phased rollouts and provides a mechanism to disable specific interventions if they produce unintended negative consequences.