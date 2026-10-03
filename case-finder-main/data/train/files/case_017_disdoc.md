- Company: Discord
- Title: Learning from structure: Discord's Entity-Relationship Embeddings
- Technology area: NLP
- Source URL: https://discord.com/blog/learning-from-structure-discords-entity-relationship-embeddings
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The project, named DERE (Discord's Entity-Relationship Embeddings), aims to create meaningful, pre-trained vector representations (embeddings) for various entities within the Discord ecosystem. These entities include users, guilds (servers), games, and others. The core problem is to map entity IDs (e.g., `guild ID`, `game ID`) to a vector that captures their complex relationships and characteristics based on the social graph. This is analogous to how Large Language Models (LLMs) create embeddings for words or tokens.

#### 1.2. Relevance & reasons

The primary motivation is to accelerate and simplify machine learning development at Discord. By providing a single, pre-trained, upstream pipeline, DERE offers a reusable signal that ML engineers can use "off the shelf." This vastly reduces the overhead that would be incurred if each model owner had to independently ingest, process, and train models on the same underlying graph data. These embeddings serve as a foundational component for a wide range of downstream applications, from analytics to user-facing recommendation features.

#### 1.3. Expectations

The expectation is that DERE will produce powerful embeddings that can be easily integrated into various ML models to improve their performance. The system is designed to be accessible to internal ML practitioners, giving them a "head start" on their projects. The embeddings are expected to be useful for fine-tuning, as features in classifiers, for nearest neighbor lookups, and in ranking and recommendation systems.

#### 1.4. Previous work

The article contrasts DERE with a simpler, related technique called "matrix factorization." Matrix factorization is described as being limited to producing embeddings from only two entity types and a single relationship (e.g., users and guilds). DERE is presented as a more advanced approach that can learn a "superposition of many entities and multiple relationships," providing a more comprehensive representation of an entity's entire relationship graph. Before DERE, individual model owners would have had to build their own data ingestion and training pipelines, leading to duplicated effort.

#### 1.5. Usage volumes and patterns

The system operates at a massive scale, processing "billions of entities and tens of billions of relationships."

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Create Meaningful Representations:** Build an entity-agnostic framework to pre-train embeddings for entities like users, guilds, and games from raw social graph data.
*   **Accelerate ML Development:** Provide a centralized, off-the-shelf embedding solution to reduce overhead and streamline the development process for downstream model owners.
*   **Improve Downstream Tasks:** Enhance the performance of various applications, including:
    *   Classification models (e.g., categorization, use-case analytics).
    *   Ranking and recommendation systems.
    *   Game similarity and discovery features (e.g., for PC/console games).
    *   Targeting for features like Quests.
*   **Enable Novel Analytics:** Provide new capabilities for generating insights from Discord's data.

#### 2.2. Anti-goals

*   **Universal Applicability:** The system is not intended for all projects. For use cases where "model interpretability matters more than raw performance," a simpler, more interpretable model is recommended over DERE.

### 3. Risks and constraints

*   **Model Stability:** A key risk is the stability of embeddings over time. Changes in embeddings between training runs could negatively impact the performance and stability of all downstream models that depend on them.
*   **Scale:** The system must be able to handle billions of entities and tens of billions of relationships, which is a significant technical constraint.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The model's performance is evaluated on its ability to perform link prediction: given a head entity and a relationship type, how often it correctly predicts the tail entity.
*   **Ranking Accuracy:** `Top 1`, `Top 10`, and `Top 50` accuracy for the correct tail entity.
*   **Mean Reciprocal Rank (MRR):** Measures the average rank of the correct tail entity.
*   **Area Under the Curve (AUC):** Overall classification performance for link prediction.
*   **Training Loss:** The overall loss value is monitored during training.

#### 4.2. Online/business metrics

*   **Quest Engagement:** The embeddings led to "big improvements" in determining player interest in specific Quests, which "helps more players earn rewards for playing them on Discord."

#### 4.3. Loss functions

*   **Triplet Margin Loss:** The primary loss function is a ranking loss that optimizes for related entities to be close in the embedding space and unrelated entities to be far apart. The formula is:
    `L = max(0, m - s_i + t_ij)`
    Where:
    *   `m` is the margin parameter (set to `0.1`).
    *   `s_i` is the score for the positive example `(h, r, t)`.
    *   `t_ij` is the score for a negative example `(h, r, t')`.
*   **Alternative Loss Functions:** The article notes that `logistic` or `softmax loss` could also be used depending on the specific use case.

### 5. Data (Dataset)

#### 5.1. Data sources

The system uses Discord's internal social graph data. It relies "solely on social graph-based features."

#### 5.2. Labeling strategy

The training is unsupervised and uses contrastive learning.
*   **Positive Examples:** All existing edges (relationships) in the graph are treated as positive examples. These are represented as `head-relation-tail (h, r, t)` triplets.
*   **Negative Examples:** Negative examples are generated "on-the-fly during train time by randomly corrupting positive examples." For a positive triplet `(h, r, t)`, a negative example might be `(h, r, t')` where `t'` is a randomly selected entity for which the relationship `r` with `h` does not exist. This is considered a safe operation due to the massive size of the training data.

#### 5.3. Data structure and examples

The data is structured as `(h, r, t)` triplets. Examples include:
*   `(user_id, in_guild, guild_id)`: A user is a member of a guild.
*   `(user_id, is_friend, user_id)`: Two users are friends.
*   `(guild_id, has_channel, channel_id)`: A channel belongs to a guild. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_017/img_017.png`)
*   `(user_id, played_game, game_id)`: A user has played a certain game. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_017/img_015.png`)

At the time of writing, the `user_in_guild` relationship was identified by `Relation 17`.

#### 5.4. Data quality and cleaning

[NO INFO]

### 6. Validation schema

#### 6.1. Train/validation/test split

The article does not specify a formal train/validation/test split strategy. Evaluation is performed via link prediction, which implies a holdout set of edges is used for testing. Negative examples for training are generated on-the-fly from positive training examples.

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Leakage risks

[NO INFO]

### 7. Baseline solution

*   **Matrix Factorization:** This technique is mentioned as a simpler alternative. It is limited to modeling a single relationship between two entity types (e.g., a user-guild interaction matrix). DERE is considered superior as it can jointly model many entities and relationship types.
*   **Simpler, Interpretable Models:** For projects where interpretability is more important than raw performance, the recommended baseline is to use a simpler model instead of DERE.

### 8. Errors and their analysis

*   **Qualitative Analysis via Visualization:** The team uses dimensionality reduction techniques like UMAP to project high-dimensional embeddings into 2D or 3D space. This allows for visual inspection to "uncover some of the structure that has been learned." An example provided is visualizing the clustering of guild embeddings for Reddit communities (e.g., guilds starting with `r/`). (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_017/img_020.png`)
*   **Performance Monitoring Over Time:** Future work includes adding features to visualize embeddings from every training run to get a more detailed view of model performance and stability over time.

### 9. Training pipelines

#### 9.1. Tooling

*   **Storage:** `Google Cloud Storage` is used for raw embedding files, and `BigQuery` is used for hosting queryable embeddings.
*   **ML Framework:** [NO INFO]

#### 9.2. Training process

The training process is based on contrastive learning with `(h, r, t)` triplets.
1.  **Embedding Lookup:** For a given triplet, the model looks up the embedding vectors for the head (`h`) and tail (`t`) entities.
2.  **Transformation:** A relation-specific transformation `g_r` (e.g., translation, diagonal multiplication) is applied to one of the entity embeddings to project them into a common space for that relation.
3.  **Scoring:** A scoring function `f_r` (e.g., dot product, cosine distance) calculates a score indicating the strength of the relationship. The full scoring function is `score(h, r, t) = c(θ_h, g_r(θ_t))`. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_017/img_018.png`)
4.  **Loss Calculation:** Using on-the-fly generated negative examples, the triplet margin loss is calculated.
5.  **Weight Updates:** The loss is used to update both the entity embedding vectors and the parameters of the relation-specific transformation models.

#### 9.3. Experimentation and iteration

DERE provides multiple pipelines at various scales. Developers can use smaller, faster-to-train pipelines for rapid prototyping and experimentation before moving to the full-scale model for production launch.

### 10. Features

#### 10.1. Feature categories

The system relies exclusively on "social graph-based features." The primary features are the entities themselves, identified by their IDs, and the relationships between them.

*   **Entity Types:** `user`, `guild` (server), `game`, `channel`, `bot`.
*   **Relationship Types:** `user_in_guild`, `is_friend`, `played_game`, `has_channel`.

#### 10.2. Feature representation

Entity IDs are mapped to dense vector embeddings. These embeddings are the primary output of the DERE system and serve as input features for downstream models.

### 11. Measuring results

#### 11.1. Offline evaluation

Offline evaluation is conducted using the link prediction task, with metrics including Top-k accuracy, MRR, and AUC as described in Section 4.

#### 11.2. A/B testing

The article implies the use of online experiments to measure business impact. For example, the integration of game embeddings into the `Quests` feature resulted in "big improvements," suggesting a comparative measurement against a control group was performed.

#### 11.3. Reporting

The development process follows a phased approach from small-scale experiments to full launch. Future plans include enhancing reporting by visualizing embeddings from each training run to monitor performance over time.

### 12. Integration and Serving

DERE embeddings are made available to internal ML practitioners through multiple channels to support different use cases. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_017/img_021.png`)

#### 12.1. Offline / Batch Access

*   **Google Cloud Storage (GCS):** Raw embedding vector files and model transforms are available for bulk processing.
*   **BigQuery:** Embeddings are hosted in tables keyed by entity ID, allowing for SQL-based access. Pre-computed nearest neighbors are also available.

#### 12.2. Online / Real-time Access

*   **Embeddings API:** A live service for online lookups of entity embeddings.
*   **Nearest Neighbors API:** A live service for finding the nearest neighbors to a given entity in the embedding space.

#### 12.3. Downstream Integration Patterns

*   **Fine-tuning:** Using the pre-trained embeddings as a starting point for task-specific models.
*   **Feature Input:** Integrating embeddings as features into classifiers and other models.
*   **Nearest Neighbor Lookup:** For similarity and recommendation tasks.

### 13. Monitoring

*   **Model Stability Monitoring:** A recently implemented system tracks the stability of embeddings over time. This helps ensure that retraining downstream models is a stable process and provides insights for model optimizations.
*   **Performance Visualization:** A planned future enhancement is to add features for visualizing embeddings from every training run, providing a more detailed, longitudinal view of model performance.
*   **Data Quality Monitoring:** [NO INFO]
*   **Engineering Metrics:** [NO INFO]

### 14. Operations

#### 14.1. Retraining cadence

The article implies a regular retraining cadence by mentioning the need to track stability over time and visualize embeddings from "every training run."

#### 14.2. Development workflow

A structured workflow is provided for internal teams using DERE:
1.  **Ideation:** Define product requirements and determine if DERE is a suitable solution (vs. a simpler, more interpretable model).
2.  **Prototyping:** Use DERE's smaller-scale pipelines for rapid experiments.
3.  **Deployment:** Launch and deploy the full-scale model.

#### 14.3. Ownership and support

DERE is managed as a centralized, upstream platform. A central team [inferred] owns the pre-training pipeline, and various "model owners" across Discord consume the embeddings for their downstream applications. This model reduces redundant work and centralizes expertise.