- Company: Zynga
- Title: Deep Reinforcement Learning in Production Part 2: Personalizing User Notifications
- Technology area: Predictive ML
- Source URL: https://towardsdatascience.com/deep-reinforcement-learning-in-production-part-2-personalizing-user-notifications-812a68ce2355
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The project's goal is to personalize the timing of daily push notifications for players of Zynga's mobile game, *Words With Friends Instant*. Most mobile applications send daily messages to their user base, and for this game, messages remind users that their friends are waiting on a move. The time at which a notification is sent is a critical driver of engagement. The problem is to determine the optimal time to send a notification to each individual user to maximize their engagement with the game.

#### 1.2. Relevance & reasons

The timing of a notification significantly impacts user behavior:
- A notification sent at a good time can lead the user to re-engage with the game.
- A notification sent at a bad time may be ignored, resulting in a missed opportunity for engagement.

The existing solution was a simple, segment-based approach that was effective as a first attempt but had clear limitations and was ready for optimization. The business goal is to increase user engagement, and a more personalized approach to notification timing was identified as a key lever.

#### 1.3. Expectations

The system is expected to answer the question: "what Action do I take for this user to increase engagement." This goes beyond simple prediction (e.g., predicting when a user is likely to play) and focuses on finding an intervention (sending a notification at a specific time) that *causes* an increase in engagement. The system should algorithmically test different strategies and adapt to changes in user patterns over time.

#### 1.4. Previous work

The previous solution was a segment-based system with the following characteristics:
- The player base was divided into 3 segments based on time zones derived from the user's country.
- All users within a segment received a notification in the evening for their respective timezone, as this was the most popular time to play.

Shortcomings of this approach included:
- **Crude Approximations:** The world has more than 3 time zones, and large countries like the US and Canada have multiple time zones, making a country-to-timezone mapping inaccurate.
- **Data Quality Issues:** The system may not have the correct country associated with all users.
- **Lack of Personalization:** A segment-based strategy does not account for individual user schedules and habits (e.g., a user working a night shift). It does not use enough player context for fine-grained personalization.

#### 1.5. Usage volumes and patterns

The system was deployed to the entire player base of *Words With Friends Instant* and runs in production for "several million players per day".

### 2. Goals and anti-goals

#### 2.1. Goals

- **Primary Goal:** Increase user engagement, measured by the click-through rate (CTR) of push notifications.
- **Ultimate Goal:** Maximize long-term rewards, such as long-term retention and engagement.
- **System Goal:** Create an automated system that continuously explores new strategies, adapts to changing user patterns, and optimizes key metrics with minimal manual tuning.

#### 2.2. Anti-goals

- The system should not simply predict when a user is likely to play. The article notes that if a user was already going to engage with the game at a certain time, sending a notification at that moment is redundant and not an effective intervention. The goal is to find an action that *increases* engagement, not just correlates with it.

### 3. Risks and constraints

- **Risk:** Sending notifications at a consistently bad time could lead to users ignoring them and potentially disengaging from the game.
- **Technical Constraint:** The problem is defined as an offline, batch reinforcement learning problem. This is because rewards (user clicks) are delayed from when the actions (sending notifications) take place. This setup is different from many academic RL problems that assume an online, simulated environment with instant feedback.
- **Organizational Constraint:** The team's expertise is in applying ML, not in researching and implementing novel RL algorithms from scratch. This led to the decision to use an off-the-shelf implementation from an open-source library.
- **Confidentiality:** To protect trade secrets, some details of the implementation have been obfuscated in the source article.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

[NO INFO]

#### 4.2. Online/business metrics

- **Click-Through Rate (CTR):** The primary online metric used to measure success. The system achieved a ~10% relative increase in CTR.
- **Long-Term Engagement & Retention:** Mentioned as the ultimate optimization goals for the RL agent.

#### 4.3. Loss functions

The system uses the Deep Q-Network (DQN) algorithm. While the specific loss function is not detailed, DQN typically minimizes the mean squared error between the predicted Q-value and the target Q-value derived from the Bellman equation (Temporal Difference error). The training process updates the neural network to better estimate the relationship between states, actions, and long-term rewards.

### 5. Data (Dataset)

#### 5.1. Data sources

The data consists of user historical interactions with previous push notifications. This data is collected daily for all eligible players.

#### 5.2. Labeling strategy

The problem is framed using reinforcement learning, where explicit labels are replaced by rewards.
- **Reward:** A positive reward is provided when a user interacts with (clicks on) a push notification. No reward is provided otherwise.

#### 5.3. Available metadata

The RL formulation uses the following components, which are assembled into trajectories of `(State, Action, Next State, Reward)` for each user:
- **State:** User's historical interactions with previous push notifications, structured as a time series over a 14-day window.
- **Action:** The hour of the day (0-23) when the next notification is sent. There are 24 possible actions.
- **Reward:** A binary signal indicating whether the user clicked the notification.
- **Next State:** The user's state after the action was taken and the reward was observed.

#### 5.4. Data quality issues

The previous segment-based system suffered from data quality issues, such as incorrect country data for users, which led to inaccurate timezone mapping. The RL system relies on direct user interaction history, which [inferred] mitigates this specific issue.

#### 5.5. ETL

A daily batch workflow is run to update the agent and generate recommendations. This workflow gathers the following data for training:
- The `State` of users from 2 days ago.
- The `Action` (hour of notification) taken 2 days ago.
- The `Next State` of the user from 1 day ago.
- The `Reward` (user engagement) from 1 day ago.

This data is assembled into trajectories for each user to be used in training.

### 6. Validation schema

#### 6.1. Train/validation/test split strategy

Unlike supervised learning, RL performance cannot be easily validated on a static, labeled dataset because the agent learns from feedback with the environment. For hyperparameter tuning, the team used a novel approach:
- They trained the agent to mimic the existing baseline strategy (the 3-timezone segmentation approach).
- Different hyperparameters were tested based on how well the agent could replicate the baseline policy.

#### 6.2. Cross-validation approach

[NO INFO]

#### 6.3. Holdout sets and update frequency

The final validation was performed via a live A/B test in production, where the RL agent's performance was compared against the baseline. The agent was rolled out to the entire player base after this test proved successful.

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

The baseline was a segment-based personalization system.
- **Logic:** The player base was split into 3 large time zones based on their country of record.
- **Action:** A notification was sent to every user in a segment during the evening for that timezone.
- **Rationale:** This was a simple first attempt to target users when they were most likely to play.
- **Performance:** This approach was functional but was outperformed by the RL agent, which delivered a ~10% relative lift in CTR.

### 8. Errors and their analysis

[NO INFO]

### 9. Training pipelines

#### 9.1. Tooling

- **ML Framework:** The system is built using Zynga's open-source library `RL Bakery`.
- **RL Algorithm Library:** `TF-Agents` (a TensorFlow library) was used for its off-the-shelf implementation of the DQN algorithm.
- **Deep Learning Backend:** `TensorFlow`.
- **Hyperparameter Choices:**
    - **Network Architecture:** A deep learning model was chosen to represent the features and the policy.
    - **Optimizer:** Standard deep learning optimizers like ADAM or SGD were considered.
    - **Exploration:** An epsilon-greedy mechanism was used for exploration. The value of epsilon starts high to encourage exploration and is reduced over time as the agent learns an effective strategy.

#### 9.2. Preprocessing, training, evaluation, and deployment automation

The entire process is automated in a daily batch workflow:
1.  **Data Collection:** Gathers `(State, Action, Next State, Reward)` trajectories from the previous two days.
2.  **Training:** The collected trajectories are used to update the existing RL agent's neural network weights via a deep learning workflow on TensorFlow.
3.  **Inference/Recommendation:** The updated agent generates batch recommendations for the optimal notification time for all eligible players.
This is described as an offline, batch RL problem.

#### 9.3. Experiment tracking and CI/CD

The article mentions the difficulty of choosing hyperparameters for RL, implying an experimentation process. However, specific tools for experiment tracking are not named.

### 10. Features

#### 10.1. Feature categories and selection criteria

The primary feature set is the `State`, which is defined as:
- **User historical interactions with previous push notifications.**
- This data is structured as a **time series** with a **14-day lookback window**.

No other features are explicitly mentioned.

#### 10.2. Feature store or batch/offline computation patterns

Features are computed in a daily batch process as part of the training pipeline.

#### 10.3. Feature importance and ablation results

[NO INFO]

### 11. Measuring results

#### 11.1. Offline evaluation methodology

For hyperparameter selection, the agent was trained and evaluated on its ability to mimic the existing, simpler segmentation-based strategy. This served as a proxy for offline evaluation before live deployment.

#### 11.2. A/B test design

- **Hypothesis:** Personalizing notification timing with an RL agent will increase click-through rates compared to the segment-based baseline.
- **Splitting:** [inferred] A standard A/B test was run, splitting users between the baseline and the new RL agent.
- **Results:** The RL agent increased the click-through rate by approximately 10% (relative) over a few days of data collection and training.
- **Decision:** Based on this success, the solution was rolled out to the entire player base of *Words With Friends Instant*.

#### 11.3. Reporting format and decision criteria

The key reported metric was the relative lift in CTR. A 10% lift was considered a success and justified a full production rollout.

### 12. Integration and Serving

#### 12.1. API design, batch vs. online serving

The system operates in a **batch serving** mode.
- A daily workflow generates recommendations for the optimal notification hour for every eligible player.
- These recommendations are then used by the notification service to schedule the messages.

#### 12.2. Infrastructure

- The system is powered by Zynga's internal `RL Bakery` library.
- It runs in production for several million players per day.
- Further details on the infrastructure are deferred to a future article in the series.

#### 12.3. SLAs, latency budgets, and fallback strategies

[NO INFO]

#### 12.4. Release cycle for models vs. infrastructure

The model is updated daily through the automated batch training pipeline.

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Day-to-day operational procedures

The system is designed to be highly automated, described as requiring "minimal tuning and no manual process." The daily batch job for training and recommendation is the core operational procedure.

#### 14.2. Retraining cadence and ownership

- **Retraining Cadence:** The RL agent is updated **every day** using fresh data from the preceding two days.
- **Ownership:** The system was developed and is [inferred] maintained by Zynga's ML Engineering team.

#### 14.3. Incident response and rollback procedures

[NO INFO]