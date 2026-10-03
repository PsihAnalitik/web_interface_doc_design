**Company**: Wayfair
**Title**: Building Scalable and Performant Marketing ML Systems at Wayfair
**Technology area**: Predictive ML
**Source URL**: https://www.aboutwayfair.com/careers/tech-blog/building-scalable-and-performant-marketing-ml-systems-at-wayfair
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

As a large e-commerce company, Wayfair runs numerous daily ad campaigns across a wide variety of formats and channels. These include digital ads (display networks, social media, online video), physical ads (direct mail postcards, catalogs), and organic outreach (email, push notifications).

The core problem is to programmatically optimize the numerous marketing decisions made every day, which include:
*   What message/content to show.
*   Where to show the content (which channel).
*   Whom to show the content to.
*   How much to pay for the ad placement.

The goal is to use machine learning to make these decisions in a scalable and performant way to improve overall marketing effectiveness.

#### 1.2. Relevance & reasons

The scale of Wayfair's marketing operations makes manual or simple heuristic-based decision-making inefficient. A systematic, data-driven approach is required to optimize performance across many campaigns and channels simultaneously. The ML system aims to improve business performance, drive incremental revenue, and achieve a "global optimization" of marketing spend, considering the entire ecosystem of customers and ad treatments.

#### 1.3. Expectations

The system is expected to:
*   Improve business performance, measured by KPIs like Return on Ad Spend (ROAS).
*   Drive true incremental revenue by identifying "persuadable" customers.
*   Adapt quickly to changes in the advertising environment, such as new campaigns, refreshed ad creatives, and updated vendor processes.
*   Optimize aggregated rewards across all marketing campaigns, not just on a per-channel basis.
*   Avoid negative customer experiences like ad fatigue or over-messaging.

#### 1.4. Previous work

Two common but limited ML approaches were previously used or considered:

1.  **General Propensity Modeling**:
    *   Predicts the likelihood of a person to buy or engage with certain products.
    *   Trained on observational data, allowing for easy retraining without experiments.
    *   Highly scalable with low maintenance costs.
    *   **Limitations**: May not perform well for all use cases, can lead to over-messaging the same audience, and can cause cross-program competition/cannibalization.

2.  **Specialized Response/Uplift Modeling**:
    *   Develops channel-specific models for pre-defined marketing programs (e.g., a retargeting program for recent site visitors).
    *   **Response models**: Target users most likely to respond to a specific ad and convert.
    *   **Uplift models**: Target "persuadables" whose conversions are directly caused by the ad treatment.
    *   **Limitations**: More costly to maintain, less generalizable, and requires regular Randomized Controlled Trials (RCTs) for data collection, which incurs operational and opportunity costs. Difficult to scale to hundreds of campaigns.

These approaches do not provide a "global optimization" as they fail to account for the full context of "customer" x "ad treatment" interactions across all channels and budget constraints.

#### 1.5. Usage volumes and patterns

The system supports "many ad campaigns each day" and makes "numerous marketing decisions" across a variety of digital and physical channels.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Global Optimization**: Optimize aggregated rewards (e.g., ROAS) across all marketing campaigns, not just individual ones.
*   **Incremental Lift**: Drive true incremental revenue by targeting persuadable customers.
*   **Adaptability**: Quickly adapt to changes in the marketing environment (new campaigns, creatives, vendor processes).
*   **Scalability**: Build a solution that is scalable and not overly costly to maintain, unlike purely channel-specific models.
*   **Dynamic Decisioning**: Balance the trade-off between exploiting the "best ads" and exploring alternative ad treatments to prevent performance degradation over time.

#### 2.2. Anti-goals

*   **Over-messaging**: The system should avoid showing too many ads to the same audience, which can harm the customer experience.
*   **Cannibalization**: The system should avoid creating competition between Wayfair's own marketing programs.
*   **Ad Fatigue**: The system should not repeatedly assign the "best" ad to a customer, as this can cause campaign performance to drop over time.
*   **Siloed Optimization**: The system should not optimize for individual channels in isolation.

### 3. Risks and constraints

*   **Data Collection Costs**: Building robust uplift models requires regular Randomized Controlled Trial (RCT) experiments, which have operational costs and opportunity costs (not showing ads to a control group).
*   **Scalability of Experiments**: Scaling RCT-based uplift modeling to hundreds of marketing campaigns is difficult.
*   **Dynamic Environment**: The advertising environment is constantly changing due to new business operations, privacy updates in the industry, and new campaign launches. The system must be able to adapt.
*   **Business Strategy Dependency**: The success of channel-specific models relies on a well-scoped business strategy with clearly defined audience eligibility and success metrics.
*   **Budget Constraints**: The system must operate within budget allocation constraints when assigning treatments.
*   **Ad Fatigue**: Always exploiting the best-predicted ad can lead to ad fatigue and a drop in campaign performance over time.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   Models are "back-tested" with data representative of each channel's operations. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_016/img_001.jpg`)

#### 4.2. Online/business metrics

*   **Primary Business KPI**: ROAS (Return on Ad Spend).
*   **Incremental Revenue**: A key goal for uplift modeling.
*   **Short-term Engagement Metrics**: Used as early signals for feedback generation.
    *   Clicks
    *   Product page views
*   **Long-term Financial Impact Metrics**: Forecasted to provide "delayed rewards" for the learning system.
    *   60-day GRS (Gross Revenue per Session/Sale) [inferred]
    *   Changes in Customer Lifetime Value (CLV) upon certain events (e.g., app installs, service signups).

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Observational Data**: Used to train general propensity models. This includes historical data on customer characteristics and engagement/purchase outcomes.
*   **Experimental Data**: Data from Randomized Controlled Trials (RCTs) is collected regularly on each program to build and validate uplift models.
*   **Near-term Engagement Data**: Clicks, product page views, and other short-term metrics are used as inputs for feedback generation models.
*   **Treatment/Reward Data**: The system observes the rewards for recent ad treatments to adapt its policies.

#### 5.2. Labeling strategy

*   **Propensity Models**: Labels are based on observed user behavior, such as "buy or engage with certain products" and "conversions."
*   **Uplift Models**: Labels are derived from RCTs to identify "persuadables"—customers whose conversions are caused by the ad treatment.
*   **Reinforcement Learning Feedback**: "Delayed rewards" (e.g., forecasted 60-day GRS) are generated by forecasting models to serve as the reward signal for the optimization models, allowing them to optimize for long-term impact using short-term signals.

#### 5.3. Data quality issues and cleaning

[NO INFO]

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

#### 6.1. Train/validation/test split strategy

*   General propensity models are trained on observational data and are back-tested.
*   Channel-specific models are back-tested using data that is most representative of each channel's specific operations.

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets

*   For uplift modeling, Randomized Controlled Trials (RCTs) are used, which inherently involves a control group (holdout) that is not shown certain ads. The "opportunity costs of not showing ads to some customers" is explicitly mentioned as a cost of this approach.

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

The final system, "WayLift," evolved from two simpler approaches that serve as baselines:

1.  **General Propensity Modeling**:
    *   **Description**: Models that predict the likelihood of a user to buy or engage. They are trained on observational data and applied across all eligible audiences for multiple marketing programs.
    *   **Pros**: Highly scalable, low maintenance cost, can be retrained without running experiments.
    *   **Cons**: May not perform well for specific use cases, can lead to over-messaging and cross-program cannibalization.

2.  **Specialized Response/Uplift Modeling**:
    *   **Description**: Channel-specific models built for well-defined marketing programs (e.g., retargeting, loyalty). Response models predict conversion likelihood for a specific ad, while uplift models predict the *incremental* impact of the ad.
    *   **Pros**: Generally perform well for well-designed programs as they are trained on highly relevant data.
    *   **Cons**: Costly to maintain, less generalizable, and require expensive and complex RCTs to collect data for uplift.

### 8. Errors and their analysis

The primary errors and limitations identified are related to the architectural approach rather than specific model prediction errors:

*   **Siloed Optimization Error**: Both baseline approaches fail to provide "global optimization" because they do not consider the full context of customer-treatment interactions across all marketing channels and budget constraints.
*   **Over-messaging and Cannibalization**: A key failure mode of the general propensity model approach is sending too many messages to the same high-propensity audience, hurting customer experience and having marketing programs compete with each other.
*   **Performance Degradation from Ad Fatigue**: A potential error in a simple optimization system is to always assign the "best" predicted ad to a customer. This can cause ad fatigue and lead to a drop in campaign performance over time. The WayLift system addresses this by incorporating exploration.

### 9. Training pipelines

#### 9.1. Tooling

[NO INFO]

#### 9.2. Preprocessing, training, evaluation, and deployment automation

*   The "WayLift" platform is designed for continuous learning and deployment.
*   **Customer Scoring Models**: Retrained at a regular cadence (quarterly or yearly) on observational data to capture new trends without interrupting business operations.
*   **Decision Optimization Models**: Online and batch learning systems are used to "constantly update and deploy" these models, typically on a daily or weekly cadence. This allows the system to automatically adapt to business and industry updates. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_016/img_004.jpg`)

#### 9.3. Experiment tracking and CI/CD

[NO INFO]

### 10. Features

The system uses a multi-layer approach where the first layer is dedicated to feature generation.

#### 10.1. Feature categories ("Customer Scoring")

The "Customer Scoring" layer consists of general propensity models that generate features providing fundamental knowledge about customers. These features include:
*   Affinity for different styles.
*   Interests in particular products or categories (e.g., beds, sofas).
*   Customer's likely position in the purchase cycle.
*   Price points that will resonate with the customer.
*   Probability to buy a product.

#### 10.2. Feature store or batch/offline computation patterns

*   The outputs from all the base propensity models in the "Customer Scoring" layer are used to construct an "interpretable low-dimensional customer vector."
*   This customer vector serves as the complete context input for the downstream "Decision Optimization" models.

#### 10.3. Feature importance and ablation

[NO INFO]

### 11. Measuring results

#### 11.1. Offline evaluation methodology

*   Models are "back-tested" to evaluate performance before deployment.

#### 11.2. A/B test design

*   **Uplift Modeling**: Requires regular Randomized Controlled Trial (RCT) experiments on each marketing program to collect data and measure incremental impact.
*   **Reinforcement Learning (WayLift)**: The platform inherently performs experimentation by using reinforcement learning algorithms to "balance tradeoffs between exploiting the 'best ads' and exploring alternative ads treatments." By constantly observing rewards for different treatments, the system learns and updates its optimal treatment policy. This serves as a continuous, automated A/B testing framework.

#### 11.3. Reporting format and decision criteria

*   The system monitors performance and observes rewards for each treatment to update its decision-making policy. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_016/img_003.jpg`)

### 12. Integration and Serving

The system is a multi-layer ML platform named "WayLift".

#### 12.1. API design, batch vs. online serving

*   The "Decision Optimization" layer uses both online and batch learning systems to update and deploy models that algorithmically optimize treatment decisions.

#### 12.2. Infrastructure and architecture

WayLift is composed of three model layers:

1.  **Customer Scoring**: A group of general propensity models trained on observational data. They produce scores that are aggregated into a low-dimensional customer vector, which serves as input for the next layer.
2.  **Decision Optimization**: A set of rules and/or ML models (including reinforcement learning) that sit on top of the customer scores. This layer takes the customer vector as input and decides the best treatment for that customer based on past engagement and outcomes from various treatments.
3.  **Feedback Generation**: A set of forecasting models that predict "delayed rewards" (long-term financial impact like 60-day GRS or CLV changes) from near-term engagement metrics (clicks, views). This allows the reinforcement learner in the optimization layer to learn quickly while still optimizing for long-term business goals.

(see image: `ml-design-doc-reviewer/data/raw_documents/images/case_016/img_004.jpg`)

#### 12.3. SLAs, latency budgets, and fallback strategies

[NO INFO]

### 13. Monitoring

*   **Model Quality / Performance**: The system "constantly observ[es] the rewards for recent treatments" and uses this feedback to update the optimal treatment decisions. This serves as a continuous monitoring loop for model performance.
*   **Business Metrics**: The platform is designed to optimize for business KPIs like ROAS, which are implicitly monitored.
*   **Input/Target Drift**: The system is designed to "quickly adapt to changes in the environment" (e.g., new campaigns, vendor updates) by regularly refreshing models (daily/weekly for optimization models) and learning from new reward data. This is an active approach to mitigating drift.

### 14. Operations

#### 14.1. Retraining cadence

*   **Customer Scoring Models**: Retrained at a quarterly or yearly cadence.
*   **Decision Optimization Models**: Refreshed and deployed at a daily or weekly cadence.

#### 14.2. Ownership

*   The development and operation of the WayLift platform is a collaboration between data scientists, ad tech engineers, and marketers.

#### 14.3. Incident response and rollback procedures

[NO INFO]