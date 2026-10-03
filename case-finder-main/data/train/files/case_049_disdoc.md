- Company: Haleon
- Title: Using Reinforcement Learning to track marketing spend
- Technology area: Predictive ML
- Source URL: https://medium.com/trusted-data-science-haleon/using-reinforcement-learning-to-track-marketing-spend-db67e843476b
- Content type: article

### 1. Problem definition

#### 1.1. Origin

At Haleon, the marketing team sought to gain more granular insights into the allocation of their marketing spend. The Data Science team was tasked with developing an internal tool to analyze the distribution of marketing spend and provide insights on Return on Investment (ROI) across different target audiences, referred to as AdGroups.

The core business question is exemplified by a campaign manager asking, "Given the performance to date with respect to dentists, should we change the spend allocation in coming weeks and how?". The system translates this into a data science problem: "Given the performance to date amongst dentists, create a model to recommend optimum spending for the future."

AdGroups are defined as groups of related keywords used to organize advertising campaigns. Examples include:
*   **Outdoor Adventure Enthusiasts**: keywords like "backpacks," "tents," "camping gear."
*   **Skin care**: keywords like "acne treatment," "anti-aging creams," "moisturisers."
*   **Nutrition**: keywords like "vitamins and supplements," "healthy eating plans," "superfoods."

#### 1.2. Relevance & reasons

The system aims to help the business make data-driven decisions on how to allocate marketing spending for optimal ROI. By providing granular insights, the project helps identify areas of waste and optimize the budget, thereby maximizing the effectiveness of marketing efforts. The key objective is to understand the causality of growth drivers and improve performance in search channels where there is potential for uplift from marketing spend.

#### 1.3. Expectations

The system is expected to function as a self-service tool for marketing campaign managers. The final output is delivered via a Power-BI dashboard that provides recommendations on budget allocation for different AdGroups. These recommendations help managers decide how to adjust spending to achieve their campaign goals.

#### 1.4. Previous work

The article frames the multi-armed bandit approach as a more sophisticated version of A/B testing, implying that traditional A/B testing was the existing or alternative method.

#### 1.5. Usage volumes and patterns

The users of the system are marketing campaign managers within Haleon. The system processes transactional marketing data that is aggregated according to pre-agreed metrics. No specific data volumes or query per second (QPS) metrics are provided.

### 2. Goals and anti-goals

#### 2.1. Goals

*   Maximize conversion rates.
*   Minimize acquisition costs, specifically cost-per-acquisition (CPA).
*   Increase Return on Investment (ROI) over time within a campaign.
*   Provide fine-grained insights and inferences regarding the distribution of marketing spend.
*   Recommend optimal future spending allocations for different AdGroups.

#### 2.2. Anti-goals

*   The system should not waste resources fully characterizing the performance of poorly performing AdGroups. The priority is to swiftly identify the AdGroups with the highest likelihood of success.

### 3. Risks and constraints

#### 3.1. Risks

*   **Concept Drift**: The preferences of target audiences are in continual change, which can make the model's learned distributions stale and its recommendations less effective over time.

#### 3.2. Constraints

*   **Data Pipeline Dependencies**: The data pipeline involves multiple parties:
    1.  An external marketing data provider collects the initial data.
    2.  A third-party firm processes and aggregates this data.
    3.  Haleon's internal Data Engineering team runs further transformations before the data is used by the model.
*   **Human-in-the-Loop**: The system provides recommendations, not automated actions. The final budget allocation decisions are made by marketing campaign managers, who use the tool's output as a guide.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Regret**: Used to assess the performance of the contextual bandit model. It is defined as the difference between the cumulative reward from the best possible policy and the model’s cumulative total of rewards over time. A smaller regret indicates better model performance.

#### 4.2. Online/business metrics

The model optimizes for key performance indicators (KPIs) chosen by the campaign manager. These can be maximized or minimized.
*   **Return on Investment (ROI)**
*   **Conversion Rate**
*   **Cost-per-acquisition (CPA)**: Calculated as `total cost of conversions / total number of conversions`.
*   **Click-through rate (CTR)**: The ratio of clicks to impressions for an ad.
*   **Cost-per-click (CPC)**: The cost paid for each click on an ad.

#### 4.3. Loss functions

The system uses a Reinforcement Learning (RL) framework (Thompson Sampling) which does not use a traditional loss function. The optimization is based on updating probability distributions based on observed rewards (derived from the business metrics) to balance the exploration-exploitation trade-off.

### 5. Data (Dataset)

#### 5.1. Data sources

The data originates from an external marketing data provider. It is then passed to a third-party firm for processing and aggregation based on pre-agreed metrics. Finally, Haleon's internal Data Engineering team queries and transforms this aggregated data for use in the model.

#### 5.2. Labeling strategy

This is an RL problem where the "labels" are rewards. The rewards are based on marketing metrics like CTR, CPA, or conversion rate, which are calculated from the transactional data associated with each AdGroup.

#### 5.3. Available metadata and history length

[NO INFO] The article states "Below is the schema of the final transformed data" but does not provide the schema.

#### 5.4. Data quality issues and cleaning/enrichment steps

[NO INFO]

#### 5.5. ETL or feature store architecture

The ETL process is a multi-stage pipeline:
1.  An external marketing data provider collects raw data.
2.  A third-party firm performs initial processing and aggregation.
3.  Haleon's Data Engineering team runs scripts using PySpark to query and transform the aggregated data into its final form for the model.

### 6. Validation schema

A traditional train/validation/test split is not described. The model's performance is evaluated continuously within the reinforcement learning framework. The Thompson Sampling algorithm iterates through the historical dataset, updating its beliefs about each AdGroup's performance. The primary evaluation metric is "regret," which measures the opportunity cost of exploration over time.

### 7. Baseline solution

*   **A/B Testing**: The article mentions the multi-armed bandit approach is a more sophisticated version of A/B testing, which can be considered the simpler baseline.
*   **Alternative MAB Algorithms**: Other popular multi-armed bandit algorithms like **Epsilon-Greedy** and **Upper Confidence Bound (UCB)** were considered before choosing Thompson Sampling.

### 8. Errors and their analysis

The primary source of error or performance degradation discussed is **concept drift**, described as the "continual change in the preferences of our target audiences."

The system addresses this through a "Contextual Bandit" approach, which relies on human intervention. Campaign managers use their domain knowledge to "alter the surroundings or context" based on the model's output and their observations. For example, if an AdGroup responds better to a certain ad color, the manager can adjust the campaign accordingly. This human-in-the-loop process serves as a mechanism for error correction and adaptation to changing conditions.

The system also accepts that it may never fully learn the true performance mean of poorly performing AdGroups, as the algorithm naturally exploits better-performing options. This is treated as an acceptable trade-off rather than an error to be fixed.

### 9. Training pipelines

#### 9.1. Tooling

*   **Cloud Platform**: Microsoft Azure
*   **Data Processing**: PySpark
*   **Model Development**: Python, with libraries such as `statsmodels`, `SciPy`, and `scikit-learn`.
*   **Visualization/Reporting**: Power-BI

#### 9.2. Pipeline steps

1.  **Data Ingestion & Transformation**: Data is ingested and transformed through the multi-stage ETL pipeline described in Section 5.5.
2.  **Distribution Learning (Thompson Sampling)**:
    *   A default flat probability distribution (e.g., a Gaussian with very large variance) is assigned to each AdGroup for a chosen metric (e.g., CPA).
    *   The algorithm iterates through the historical dataset day-by-day. For each observation, it updates the parameters (mean and standard deviation) of the distribution for the corresponding AdGroup.
    *   This process refines the distributions, making them narrower as more data is processed, reflecting increased confidence in the estimated mean performance.
3.  **Recommendations Optimiser**:
    *   After learning the distributions, a simulation is run for a set number of trials (e.g., 100).
    *   In each trial, a random value is drawn from each AdGroup's learned distribution.
    *   The AdGroup with the "best" value (highest for metrics like CTR, lowest for metrics like CPA) is declared the winner of that trial and awarded one point.
    *   After all trials, the percentage of total points for each AdGroup determines its recommended budget allocation (e.g., 40 wins out of 100 trials = 40% budget allocation).
4.  **Reporting**: The final budget allocation percentages are displayed on a Power-BI dashboard for campaign managers.

#### 9.3. Experiment tracking and CI/CD

[NO INFO]

### 10. Features

#### 10.1. Feature categories

*   **Arms**: The primary entities in the model are the "arms" of the bandit, which are the **AdGroups**. These are defined by marketing teams based on groups of related keywords.
*   **Context**: The system is extended into a "Contextual Bandit" where the environment's status is considered. This context is supplied by human intervention from campaign managers. An example given is an AdGroup's preference for a specific color in an advertisement.

#### 10.2. Feature selection criteria

[NO INFO]

### 11. Measuring results

#### 11.1. Offline evaluation methodology

Offline evaluation is performed by the **Recommendations Optimiser**. This component simulates a series of choices to determine budget allocation. It runs a set number of trials (e.g., 100), and in each trial, it samples a performance value from the learned statistical distribution of each AdGroup. The AdGroup that performs best in a trial (e.g., highest CTR or lowest CPA) is selected. The final recommended budget for an AdGroup is proportional to the number of trials it "won".

#### 11.2. A/B test design

The multi-armed bandit algorithm itself is presented as a dynamic alternative to traditional A/B testing. The article does not describe a separate A/B test for validating the system against a control group.

#### 11.3. Reporting

Results are presented to marketing campaign managers via a self-service Power-BI dashboard. The dashboard displays the recommended budget allocation percentages for each AdGroup, which managers use to inform their spending decisions.

### 12. Integration and Serving

#### 12.1. API design, batch vs. online serving

The system operates in a **batch** mode. It processes historical data to generate a set of recommendations. There is no real-time serving API. The "serving" layer is the Power-BI dashboard where the batch output is displayed.

#### 12.2. Infrastructure

*   **Cloud**: Microsoft Azure
*   **Dashboarding**: Power-BI

#### 12.3. SLAs, latency budgets, and fallback strategies

SLAs and latency budgets are not applicable as this is not a real-time serving system. The primary fallback strategy is the expertise of the campaign managers. Since the system provides recommendations rather than executing automated actions, managers can choose to ignore the recommendations and rely on their own judgment or previous strategies if the model's output seems incorrect.

### 13. Monitoring

#### 13.1. Data quality and schema checks

[NO INFO]

#### 13.2. Model quality and prediction drift

*   **Model Quality**: The **regret metric** is used to assess the model's performance over time, comparing its cumulative reward to that of an optimal policy.
*   **Prediction/Concept Drift**: The system explicitly acknowledges the risk of drift due to "continual change in the preferences of our target audiences." This is monitored and mitigated through the **Contextual Bandit** approach, where campaign managers provide feedback and adjust context based on real-world campaign performance, effectively acting as a human-in-the-loop monitoring system.

#### 13.3. Engineering metrics

[NO INFO]

### 14. Operations

#### 14.1. Retraining cadence

The article describes the model learning process as an iteration through the dataset, but does not specify a recurring retraining cadence. [inferred] Given the focus on changing audience preferences, the model is likely updated periodically as new performance data becomes available.

#### 14.2. Ownership

*   **Data Science Team**: Develops and maintains the reinforcement learning model and the recommendation engine.
*   **Data Engineering Team**: Manages the data pipeline that feeds the model.
*   **Marketing Campaign Managers**: End-users of the tool. They consume the recommendations from the Power-BI dashboard and provide the "human intervention" or context required for the Contextual Bandit approach.

#### 14.3. Incident response and rollback procedures

[NO INFO] Since the system provides non-binding recommendations, a "rollback" would consist of the campaign manager disregarding the tool's output and using an alternative budget allocation strategy.