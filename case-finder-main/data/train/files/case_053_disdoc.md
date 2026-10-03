- Company: LinkedIn
- Title: Building a Large-Scale Recommendation System: People You May Know
- Technology area: Predictive ML
- Source URL: https://www.linkedin.com/blog/engineering/recommendations/building-a-large-scale-recommendation-system-people-you-may-know
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The "People You May Know" (PYMK) feature is a core part of LinkedIn's platform, designed to help members form connections and expand their professional networks. The system recommends other members that a user may want to connect with. The user base consists of over one billion members, leading to a monumental task of selecting a relevant candidate pool for each user.

#### 1.2. Relevance & reasons

The feature is essential to LinkedIn's mission of connecting professionals. Members have various motivations for connecting, including:
- Finding a professional mentor.
- Networking with a future employer.
- Reestablishing connections with peers from school.

The primary technical challenge is the scale of the candidate inventory. It is impossible to score every potential connection (hundreds of billions daily) for every user within a reasonable time frame. The system must efficiently sift through this massive pool to generate relevant recommendations.

#### 1.3. Expectations

The system is expected to generate a final recommendation list that balances multiple objectives:
- High relevance for the user (inviter).
- High likelihood of the connection bringing value to both the inviter and invitee.
- Fairness and diversity in recommendations.
- Low serving latency.

The system optimizes for multiple factors, such as the likelihood of a user sending an invitation and that invitation being accepted.

#### 1.4. Previous work

The article describes the evolution of the PYMK system over the last two years, culminating in the current multi-stage ranking architecture. This new system is credited with delivering some of the biggest improvements in member engagement and retention in the past six years.

#### 1.5. Usage volumes and patterns

- **Users**: Over one billion members.
- **Data Volume**: Processes hundreds of terabytes of data daily.
- **Candidate Pool**: Hundreds of billions of potential connections are considered daily.

### 2. Goals and anti-goals

#### 2.1. Goals

- **Primary Goal**: To build a high-quality, large-scale recommendation system that helps members form valuable connections.
- **Relevance**: Maximize the likelihood of a user sending an invitation and the invitation being accepted.
- **Fairness**: Ensure fairness in recommendations with respect to protected attributes like gender and age.
- **Diversity**: Ensure that recommendations reflect varied interests and intents.
- **Coverage**: Ensure the most relevant candidates from a pool of billions are considered in the ranking process.
- **Performance**: Maintain low serving latency despite the massive scale.

#### 2.2. Anti-goals

- **Avoid Overrepresentation**: The system should not overrepresent platform power users in the recommendations.
- **Avoid Full Scoring**: The system must avoid sifting through the entire candidate inventory for scoring due to computational infeasibility.

### 3. Risks and constraints

- **Technical Constraint**: The primary constraint is the size of the candidate pool (billions of items), which makes exhaustive scoring for inference computationally prohibitive.
- **System Complexity**: The multi-stage architecture poses challenges in terms of maintainability and monitoring.
- **Stage Coupling**: There is a trade-off between tight coupling of stages (which can increase accuracy) and loose coupling (which increases development speed).
- **Feedback Loops**: Tackling feedback loops in a multi-stage system is a significant challenge that has not been systematically explored.
- **Offline-Online Discrepancy**: Offline metrics rarely match online performance, requiring reliance on A/B testing for final evaluation.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The system uses a multi-stage architecture, with each stage evaluated by specific offline metrics:

- **L0 (Candidate Generation)**:
    - **Metric**: Recall@k
    - **Rationale**: The goal is to ensure the most relevant candidates are selected for the next stage, not to rank them perfectly.
    - **Value**: k is in the 3,000-5,000 range.

- **L1 (Light Ranker)**:
    - **Metric**: Recall@k
    - **Rationale**: To ensure the reduced set of candidates still contains the most relevant items.
    - **Value**: k is in the 500-800 range.

- **L2 (Rich Ranker)**:
    - **Metrics**: AUC, Precision@k, Expected Calibration Error (ECE).
    - **Rationale**: This stage requires high-precision ranking. ECE is important because the output scores are used in subsequent stages and by other teams, requiring them to be well-calibrated probabilities.

- **Re-Ranker**:
    - **Metrics**: Log-likelihood, diversity metrics.
    - **Rationale**: To evaluate the quality of the final ranked list after applying business rules, fairness, and diversity adjustments.

#### 4.2. Online/business metrics

- **Evaluation Method**: A/B testing is the trusted method for evaluating the overall system's performance.
- **Key Metrics**: Member engagement and retention.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

- **Primary Source**: LinkedIn's member graph, containing over one billion members and their connections.
- **Data Types**:
    - Member profile data.
    - Graph connection data (e.g., n-hop neighbors).
    - Member interaction data (e.g., invitations sent, invitations accepted).

#### 5.2. Labeling

- **Proxy Labels**: The system predicts engagement events, so the labels are derived from user actions.
    - Positive label: A user sends an invitation to a recommended member.
    - Positive label: A sent invitation is accepted.

#### 5.3. Data quality and preprocessing

[NO INFO]

#### 5.4. ETL

The system processes hundreds of terabytes of data daily. The article mentions methods like Negative Sampling, Adaptive Importance Sampling, and Hierarchical Softmax are used to help scale the *training* process, but does not detail the ETL architecture.

### 6. Validation schema

The article mentions a discrepancy between the distribution of offline training data and online data but does not describe the specific train/validation/test split strategy.

[NO INFO]

### 7. Baseline solution

The article does not describe a simple baseline that the current system was compared against. Instead, it details the current advanced multi-stage architecture. The L0 stage does include "simple heuristic sources" (e.g., new members in a geographic area) alongside more complex graph and embedding-based sources.

### 8. Errors and their analysis

The article highlights the discrepancy between offline and online evaluation results, attributing it to several factors:

- **Presentation Biases**: Factors in the user interface that affect user behavior, such as a missing profile photo, UI lag, or position bias.
- **Deployment Errors**: Unintentional errors introduced when deploying models to production.
- **Data Distribution Discrepancy**: The distribution of offline training data does not perfectly match the distribution of data seen in the online production environment.
- **Feedback Loops**: A known challenge in complex, multi-stage systems that is not yet systematically solved.

### 9. Training pipelines

#### 9.1. Tooling

[NO INFO]

#### 9.2. Pipeline stages

The article mentions that methods are used to scale the training process, but does not describe the full pipeline.
- **Scaling Techniques**: Negative Sampling, Adaptive Importance Sampling, and Hierarchical Softmax are used to manage the large scale during model training.
- **Model Types**:
    - Lightweight models (Logistic Regression, XGBoost) are used in the L1 stage.
    - Deep Neural Networks are used as heavy models in the L2 stage.
- **Parameter Optimization**: Bayesian optimization is used in the re-ranking stage to estimate the weights for combining scores from different L2 models.

### 10. Features

#### 10.1. Feature categories

- **Graph-based Features**: Derived from the social graph, such as n-hop neighbors and features from random graph walks.
- **Embedding-based Features**: Candidates generated via similarity scores from embeddings (Embedding-Based Retrieval or EBR).
- **Heuristic Features**: Simple, rule-based features, such as "new LinkedIn members in your geographic area."
- **Member-Candidate Pair Features**: Described as "most powerful" features used by the L2 deep learning models.
- **Protected Attributes**: Attributes like gender and age are used in the re-ranking stage to ensure fairness.

#### 10.2. Feature store

[NO INFO]

### 11. Measuring results

#### 11.1. Offline evaluation

Each stage of the ranking funnel is evaluated with specific offline metrics (see Section 4.1). This allows for stage-wise optimization and debugging.

#### 11.2. A/B testing

- **Hypothesis**: Changes to the multi-stage ranking system will improve member engagement and retention.
- **Primary Method**: A/B tests are considered the source of truth for system performance due to the unreliability of offline metrics in predicting online outcomes.
- **Results**: The launch of the multi-stage ranking system delivered "some of the biggest improvements in member engagement and retention in the past 6 years."

### 12. Integration and Serving

The system is designed as a multi-stage ranking architecture that acts as a funnel, progressively reducing the candidate set.

- **L0 Ranking (Candidate Generation)**:
    - **Goal**: Select a few thousand candidates from an inventory of billions. Prioritizes recall.
    - **Methods**: Combines multiple candidate generation (CG) sources:
        - Graph-based sources (e.g., n-hop neighbors, random graph walks).
        - Embedding-Based Retrieval (EBR) sources.
        - Simple heuristic sources.

- **L1 Ranking (Light Ranker)**:
    - **Goal**: Reduce the candidate set from thousands to a few hundred (500-800).
    - **Methods**: Uses a lightweight model (e.g., Logistic Regression, XGBoost) to calibrate scores from diverse L0 sources and rank them against a common objective.

- **L2 Ranking (Rich Ranker)**:
    - **Goal**: Precisely rank the most relevant candidates from the reduced set.
    - **Methods**: Employs multiple heavy deep neural network models that predict the probability and value of different engagement events (e.g., invitations sent, invitations accepted).

- **Re-Ranker (Final Stage)**:
    - **Goal**: Apply final adjustments for business objectives, fairness, and diversity.
    - **Methods**: Consists of multiple re-rankers:
        - **Fairness Re-rankers**: Ensure fairness based on protected attributes (gender, age).
        - **Diversity Re-rankers**: Ensure varied interests and intents are represented.
        - **Business Rule Re-rankers**: Avoid outcomes like overrepresenting platform power users.
    - **Optimization**: The scores from the L2 models are linearly combined. The weights for this combination are estimated using Bayesian optimization.

#### 12.1. SLAs

The system is designed to ensure "low serving latency" while handling a massive candidate inventory.

### 13. Monitoring

The article notes that monitoring such a complex system is a continuing challenge. No specific tools, metrics, or alerting strategies are mentioned.

[NO INFO]

### 14. Operations

The article mentions that maintainability is a challenge for such a complex system. No details are provided on retraining cadence, incident response, or rollback procedures.

[NO INFO]