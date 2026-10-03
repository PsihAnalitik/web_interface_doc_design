- Company: Glassdoor
- Title: Personalized Fishbowl Recommendations with Learned Embeddings: Part 2
- Technology area: Recommender system
- Source URL: https://medium.com/glassdoor-engineering/personalized-fishbowl-recommendations-with-learned-embeddings-part-2-78a16b04d396
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The system is designed to provide personalized post recommendations to users on Fishbowl, a professional networking community acquired by Glassdoor. On Fishbowl, users anonymously post and comment in "bowls" or "feeds," which are collections of posts related to specific industries or topics. The core problem is to rank and recommend relevant posts to users to improve their engagement.

#### 1.2. Relevance & reasons

The primary challenge is the absence of clear negative signals from user clickstream data. Users provide positive signals by "liking" posts, but there is no explicit "dislike" action. This makes it difficult to use standard supervised learning setups for ranking. The goal is to move beyond simple content-based similarity to a more holistic recommendation model that incorporates multiple features and collaborative signals.

#### 1.3. Expectations

The system is expected to generate a ranked list of posts for each user. The ranking should be based on the likelihood that the user will find the post interesting, with the ultimate goal of driving positive interactions (e.g., likes). The model should be able to generalize to new users and new posts.

#### 1.4. Previous work

A previous version of the system used a Doc2Vec model.
*   **Post Embeddings**: A Doc2Vec model was trained on the Fishbowl post corpus to generate text embeddings for each post.
*   **User Embeddings**: A user's embedding was calculated as the average of the post text embeddings of all the posts they had liked.
*   **Collaborative Signal**: To incorporate a collaborative notion, the embeddings of other users who liked a post were also averaged into the post's final embedding.
*   **Ranking**: Cosine similarity between user and post embeddings was used to rank posts.

This approach had shortcomings: it only used post text as a feature and was trained on a relatively small, domain-specific corpus, which limited the quality of the text embeddings.

#### 1.5. Usage volumes and patterns

[NO INFO]

### 2. Goals and anti-goals

#### 2.1. Goals

*   Improve recommendation quality by incorporating a richer set of features beyond just post text.
*   Leverage transfer learning from large pre-trained language models (GloVe, BERT) to improve embedding quality.
*   Learn user and post embeddings tailored to the recommendation task using neural networks.
*   Develop a system that can serve as a first-stage candidate generation/filtering mechanism for a larger ranking pipeline.

#### 2.2. Anti-goals

*   Avoid overly complex models that overfit the training data. The experiments showed that simpler models generalized better than deep neural networks for this specific dataset.
*   The system is not intended to be the final, single-stage ranking model but can be used for candidate retrieval before a more complex supervised ranking stage.

### 3. Risks and constraints

*   **Data Sparsity / Lack of Negative Signals**: The primary constraint is the lack of explicit negative feedback. Implicit negatives must be sampled, which introduces the risk of "false negatives" (sampling a post the user might have liked but hadn't seen).
*   **Cold Start Problem**: The system needs to generate recommendations for new users and new posts. The design addresses this by learning a generalized function based on features, rather than learning embeddings for user/post IDs (as in methods like DeepWalk).
*   **Model Overfitting**: The neural network models (Siamese, GCN) were found to converge very quickly (3 epochs) and then overfit, indicating a risk with overly complex architectures on this dataset.
*   **Scalability of Graph Methods**: For the GCN approach, pooling features from all K-hop neighbors is computationally expensive. This is mitigated by sampling a fixed number of neighbors (up to 50).

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The model is evaluated on its ability to predict which posts a user will like in a holdout test period.

*   **Precision@K**: The percentage of recommended posts in the top K that the user actually liked during the test period.
*   **Recall@K**: The percentage of all posts that the user liked during the test period that were present in the top K recommendations.

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

A **contrastive triplet loss** function is used for training the Siamese and Graph Convolutional Network (GCN) models.
*   **Objective**: To minimize the distance between an anchor (user) and a positive sample (a post the user liked) while maximizing the distance between the anchor and a negative sample (a post the user did not like).
*   **Formulation**: The loss is based on the difference between the cosine similarity of the (user, negative_post) pair and the (user, positive_post) pair. The model is encouraged to learn similar embeddings for positive pairs and dissimilar embeddings for negative pairs.
*   **Pairs Generation**:
    *   **Anchor**: A user.
    *   **Positive**: A post the user liked.
    *   **Negative**: A randomly sampled post. Two strategies were used:
        1.  **Simple Negative**: A randomly selected post from the same feed as the positive post.
        2.  **Hard Negative**: A post from a bowl the user is subscribed to, which is among the top 25 liked posts in that bowl, and which the user never liked. This is designed to reduce exposure bias.

### 5. Data (Dataset)

#### 5.1. Data sources

The data is sourced from the Fishbowl platform and includes:
*   **User-Post Interactions**: Records of which users "liked" which posts. This forms the basis for positive training pairs.
*   **Post Content**: The text of each post.
*   **User Profile Data**: Self-reported information provided by users at sign-up, including employer, job title, and work city.
*   **Feed (Bowl) Metadata**: The name and description of the feed where a post was made.
*   **Post Engagement Metrics**: Counts of 5 reaction types (Like, Helpful, Smart, Funny, Uplifting), total reactions, number of comments, and number of shares.

#### 5.2. Labeling strategy

The system uses a self-supervised approach based on implicit signals.
*   **Positive Labels**: A (user, post) pair is considered positive if the user liked the post.
*   **Negative Labels**: Negative samples are generated on the fly during training.
    *   **Initial Strategy**: A randomly selected post from the same feed as the positive post. This assumes that if a user has liked only a few posts in a large feed, a random post from that feed is likely a true negative.
    *   **Hard Negative Sampling**: To create stronger negative signals, a "hard negative" is defined as a popular post (top 25 liked) in a feed the user subscribes to but did not interact with. This increases the probability that the user saw the post and chose not to engage.

#### 5.3. Data quality issues and cleaning

*   **Limited Corpus Size**: The internal Fishbowl corpus of posts and comments was considered not large enough to train high-quality language models from scratch, motivating the use of transfer learning with pre-trained models.
*   **Feature Correlation**: Many input features are highly correlated (e.g., a post about a company in a bowl for that same company). This was a motivation for using PCA to reduce dimensionality and noise.

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

*   **Train/Test Split**: A time-based split is used. The models are trained on 12 months of historical data.
*   **Test Set**: The models are evaluated on the subsequent week of data immediately following the training period.
*   **Leakage Prevention**: To avoid data leakage, user embeddings for the test period are generated using only information from the training data. Post embeddings are generated for all posts the user was eligible to see during the test week.

### 7. Baseline solution

The baseline for comparison is the previous Doc2Vec-based model.
*   **Model**: Doc2Vec trained on the Fishbowl post corpus.
*   **Embeddings**:
    *   Post embeddings were generated directly from the Doc2Vec model.
    *   User embeddings were the average of the embeddings of posts the user liked.
    *   A collaborative component was added by averaging in the embeddings of other users who liked a given post.
*   **Ranking**: Cosine similarity between user and post embeddings.
*   **Performance**: The new GloVe-based model performed better than this baseline.

### 8. Errors and their analysis

*   **Model Complexity vs. Performance**: The more complex neural network models (Siamese, GCN) performed worse than the simpler GloVe-based aggregation model. They overfit the training data quickly (within 3 epochs), even with the introduction of hard negatives. This suggests the dataset does not warrant a highly complex model, and simpler aggregation is more robust.
*   **Impact of PCA**: Adding a PCA step to reduce the 600-dimension concatenated GloVe embedding to 128 dimensions improved model performance. The hypothesis is that PCA removes noise from less useful feature values and condenses information from highly correlated features, leading to better generalization.
*   **Effectiveness of Negative Sampling**: The authors suspect that the performance of the neural network models could be improved with a better negative sampling strategy, as some improvement was observed when switching from simple random negatives to hard negatives.
*   **GCN vs. GloVe Aggregation**: The GloVe model's manual aggregation (averaging embeddings of users who liked a post) is conceptually similar to a 1-hop GCN. The key difference is that the GCN learns weights for aggregation, whereas the GloVe model uses a simple, unweighted average. The superior performance of the GloVe model suggests that its reduced complexity helped prevent overfitting in this context.

### 9. Training pipelines

#### 9.1. Tooling

*   **Language Models**: Pre-trained GloVe (100-dim) and BERT models were used.
*   **Dimensionality Reduction**: Principal Component Analysis (PCA).
*   **ML Framework**: A neural network framework `[inferred]` (like PyTorch or TensorFlow) was used to build the Siamese and GCN models, which consist of linear layers and ReLU activations.

#### 9.2. Preprocessing and Training

**Transfer Learning Fine-Tuning:**
*   **GloVe**: The pre-trained GloVe model was fine-tuned on the custom Fishbowl corpus of post texts and comments.
*   **BERT**: The pre-trained BERT model was fine-tuned on a concatenated "document" for each post, created by joining the six text features: `CONCAT(user company, user title, user location, post text, feed_name, feed description)`. This allows the model to learn contextual representations across all text features simultaneously.

**Model Training:**
*   **GloVe/BERT Models**: These are not trained in an end-to-end fashion for the recommendation task itself. Instead, the fine-tuned models are used to generate embeddings as features, which are then aggregated.
*   **Siamese & GCN Models**:
    *   Trained for 3 epochs to prevent severe overfitting.
    *   The training process uses a contrastive triplet loss.
    *   Positive and negative pairs are generated on the fly.
    *   For the GCN, neighbor sampling is used to control computational complexity, with up to `T=50` neighbors sampled based on node degree.

### 10. Features

#### 10.1. Feature categories

**1. Text-Based Content Features (6 total):**
*   **Post Text**: The text of the Fishbowl post.
*   **Company**: The employer of the post's author.
*   **Job Title**: The job title of the post's author.
*   **City Location**: The work city of the post's author.
*   **Feed Name**: The name of the bowl the post was made in.
*   **Feed Description**: The description of the bowl.
*   *Note: For user embeddings, post-specific features like "Post Text" are represented by an empty string or zero vector.*

**2. Post Popularity Features (8 total):**
*   **Reactions**: Like, Helpful, Smart, Funny, Uplifting.
*   **Engagement**: Total reactions, number of comments, number of shares.
*   *Note: These features are scaled before use.*

#### 10.2. Feature engineering

The core of the system is the creation of user and post embeddings through a multi-step feature engineering process.

**For the GloVe-based model (the production model):**
1.  **Word Embeddings**: For each of the 6 text features, generate word embeddings using the fine-tuned GloVe model.
2.  **Sentence/Phrase Embeddings**: For features containing multiple words (e.g., Post Text), the final feature embedding is the mean of its constituent word embeddings. This results in six 100-dimensional embeddings.
3.  **Concatenation**: The six 100-dim text feature embeddings are concatenated into a single 600-dim vector. The 8 scaled popularity features are then concatenated to this vector.
4.  **Dimensionality Reduction**: PCA is applied to reduce the final concatenated vector to 128 dimensions. This is the "content embedding".
5.  **Collaborative Aggregation**:
    *   **Final Post Embedding**: The post's content embedding is added to the average content embedding of all users who liked that post.
    *   **Final User Embedding**: The user's content embedding is added to the average content embedding of all posts that the user liked.

**For the BERT-based model:**
*   The process is similar to the GloVe model, but word embeddings are generated from a fine-tuned BERT model by taking the average output of the last 4 attention layers.

**For Siamese/GCN models:**
*   The pre-computed GloVe content embeddings (before collaborative aggregation) are used as input features to the respective neural networks. The networks then learn a function to produce the final user/post embeddings.

### 11. Measuring results

#### 11.1. Offline evaluation

*   **Methodology**:
    1.  Train models on 12 months of data.
    2.  For each user in the 1-week test set, generate their embedding using training data.
    3.  Generate embeddings for all posts they were eligible to see in the test week.
    4.  Rank all eligible posts for the user based on the cosine similarity between the user and post embeddings.
    5.  Evaluate the top K ranked posts against the posts the user actually liked using Precision@K and Recall@K.
*   **Results**:
    *   The GloVe embedding model with 6 input features and PCA reduction performed the best.
    *   This model outperformed the Doc2Vec baseline.
    *   The Siamese and GCN models performed slightly worse than the GloVe model, likely due to overfitting.

#### 11.2. A/B test design

The article states that the "GloVe based embedding model with PCA is also the model we shipped for testing in production." This implies an A/B test was conducted, but no details on the hypothesis, splitting methodology, duration, or statistical criteria are provided.

### 12. Integration and Serving

#### 12.1. API design and serving pattern

The system is designed to be used as a **first-stage candidate generation** model in a larger recommendation pipeline.
*   **Pattern**: Embeddings for users and posts are likely pre-computed in a batch process.
*   **Retrieval**: At serving time, for a given user, a fast K-Nearest Neighbors (K-NN) search is performed over the vast corpus of post embeddings to retrieve a set of candidate posts.
*   **Re-ranking**: These candidates can then be passed to a more complex, supervised learning model for final re-ranking.

#### 12.2. Infrastructure

[NO INFO]

#### 12.3. SLAs and fallback

[NO INFO]

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Retraining cadence

The validation schema of training on 12 months of data suggests a periodic retraining schedule, but the exact frequency (e.g., daily, weekly, monthly) is not specified.

#### 14.2. Incident response and rollback

[NO INFO]