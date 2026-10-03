**Company**: Dropbox
**Title**: Optimizing payments with machine learning
**Technology area**: Predictive ML
**Source URL**: https://dropbox.tech/machine-learning/optimizing-payments-with-machine-learning
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The system addresses involuntary churn caused by payment failures for Dropbox subscriptions. When a recurring payment fails, the customer enters a "renewal failure" state. If payment is not recovered within a certain window, the customer's account is downgraded to a free Basic account. This is a negative customer experience and results in lost revenue for Dropbox.

The problem is to optimize the payment retry strategy during the renewal failure window to maximize the probability of a successful charge and minimize involuntary churn. The problem is framed as a multi-armed bandit problem: given a limited number of retries, determine the best time to use them.

#### 1.2. Relevance & reasons

- **Poor Customer Experience**: Downgrades are a poor experience for active users and teams who believe they have a paid subscription. This can cause negative feelings about the brand.
- **Lost Revenue**: Involuntary churn disrupts a steady flow of revenue. A customer who is downgraded might not return.
- **Inefficiency of Existing System**: The previous system was based on a static set of rules that were manually maintained and had hit a performance ceiling.

#### 1.3. Expectations

The goal is to find an optimal billing policy that is superior to the existing hardcoded rules. The system should be able to determine when to retry a charge, how many times, and whether a retry should be attempted at all. The solution should also reduce the manual effort required to maintain the billing logic.

#### 1.4. Previous work

Historically, the Dropbox Payments Platform used a static set of about ten different hardcoded rule sets to manage renewal failures.
- **Example Rule**: "Charge a customer every four days until a payment succeeds, for a maximum of 28 days."
- **Manual Optimization**: The Payments team manually segmented users (by subscription type, geography, etc.) and A/B tested the rule sets to find the best-performing one for each segment. This was complex, time-consuming, and the rules decayed in performance over time.
- **A/B Test Validation**: Early A/B tests proved that the timing of a charge attempt had a significant effect on its success rate, validating the premise for a more sophisticated optimization approach.

#### 1.5. Usage volumes and patterns

The Dropbox Payments Platform manages payment processing for millions of customers with monthly or yearly subscription cadences.

### 2. Goals and anti-goals

#### 2.1. Goals

- **Primary Business Goal**: Increase the overall payment charge success rate (Invoice Approval Rate) and reduce involuntary churn.
- **Secondary Business Goal**: Reduce the time to collect payment (collection time).
- **System Goals**:
    - Replace manual intervention and complex, static rule-based logic with an automated, ML-driven system.
    - Achieve global optimization of multiple parameters for specific customer segments.
    - Build a system that is robust to changes in customer behavior and market conditions.
    - Keep the overall system complexity low.

#### 2.2. Anti-goals

- **Creating a more complex system**: An initial design using a separate model for each payment retry attempt was rejected because it went against the goal of reducing system complexity. The final design uses a single, reusable model.

### 3. Risks and constraints

#### 3.1. Technical constraints

- **Prediction Latency**: The initial design, where the model was loaded directly into the Payments Platform, resulted in prediction latencies of around two minutes, which was too high. The final design required latency under 300ms for 99% of requests.

#### 3.2. Other risks

- **Performance Decay**: The performance of the manually curated rule-based system was observed to decay over time. The ML system is designed to stay "sharp" through retraining.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

[NO INFO]

#### 4.2. Online / business metrics

- **Invoice Approval Rate**: The primary business metric. It measures whether a user's subscription renewal was ultimately successful within the billing cycle. A single invoice tracks all payment attempts for a specific renewal.
- **Attempt Success Rate**: A secondary metric that tracks the success rate of each individual payment attempt. This helps measure how quickly a customer's subscription is successfully renewed.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The data consists of internal signals related to customer accounts and payment history.
- Dropbox account usage patterns.
- Payment failure history (e.g., types of failures).
- Payment type characteristics.
- Information about the previous failure.

This data is stored in **Edgestore**, Dropbox's primary metadata storage system.

#### 5.2. Labeling

[NO INFO]

#### 5.3. ETL

- A daily scheduled **Airflow** job collects the most recent usage and payment signals for customers.
- This data is stored in Edgestore to be available for the prediction service.

#### 5.4. Data quality issues

[NO INFO]

### 6. Validation schema

#### 6.1. Train/validation/test split

[NO INFO]

#### 6.2. A/B testing

- A/B testing is the primary method for validating the model's impact in production.
- Dropbox's internal feature gating service, **Stormcrow**, is used to randomly sample user segments for tests.
- The initial model (optimizing only the first retry) was validated with an A/B test on a random sample of US individual users and shipped after showing improvement.
- The end-to-end model was being A/B tested on Dropbox teams at the time of writing.

### 7. Baseline solution

The baseline was the existing system used by the Payments Platform for over 14 years.
- **Type**: A static, rule-based system.
- **Logic**: Consisted of about ten different hardcoded rule sets. A typical rule was to retry a charge every four days for a maximum of 28 days. Other rules included logic like "Avoid Weekends".
- **Selection**: The Payments team would manually A/B test these rules on different user segments (based on geography, subscription type) and set the best-performing rule as the default for that population.
- **Performance**: This approach had hit a performance ceiling and required significant manual effort to maintain.

### 8. Errors and their analysis

#### 8.1. Payment failure reasons

Payment failures, which trigger the renewal recovery process, can occur for several reasons:
- Insufficient funds
- Expired credit card
- Disabled credit card (e.g., reported lost or stolen)
- Transient processing failures

#### 8.2. System design errors

An early design iteration involved using a separate model for each payment retry attempt (e.g., a model for the 1st retry, another for the 2nd, etc.). This was deemed an error because it created a more complicated system, which was against a secondary goal of the project. This led to the revised approach of using a single model that could be called multiple times.

### 9. Training pipelines

#### 9.1. Automation

- Data collection jobs are automated to run daily using Airflow.
- The system is designed for models to be retrained to stay "sharp" and adapt to changing patterns, though the specific cadence is not mentioned.

#### 9.2. Tooling

- **Airflow**: Used for automating daily data collection jobs.

### 10. Features

#### 10.1. Feature categories

The gradient boosted ranking model is trained with features including:
- Types of payment failures
- Dropbox account usage patterns
- Payment type characteristics

### 11. Measuring results

#### 11.1. A/B test design

- **Hypothesis**: An ML-based retry schedule will outperform the static rule-based schedule, leading to a higher Invoice Approval Rate.
- **Splitting**: Random sampling of user segments (e.g., US individual users, Dropbox teams) is performed using the internal `Stormcrow` feature gating service.
- **Decision Criteria**: The model is shipped if it demonstrates a statistically significant improvement in success rates compared to the control group (rule-based system).

### 12. Integration and Serving

#### 12.1. Architecture evolution

- **Initial Architecture**: The model was loaded and run directly within the Payments Platform service.
    - **Problems**: This caused the Payments Platform to "bloat significantly" due to added dependencies. Prediction latency was high, averaging around **two minutes**.
- **Final Architecture**: The model is served via a centralized ML platform service.
    - **Components**: A `predict module` acts as an intermediary between the `Payments Platform` and the `Predict Service`.
    - **Benefits**: This provided a clean separation of concerns, allowed for easy scaling, and dramatically reduced prediction latency to **under 300ms for 99%** of requests.

#### 12.2. Serving workflow

The serving workflow uses a combination of the Payments Platform and a centralized ML system. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_002/img_006.webp`)

1.  **Trigger**: A payment attempt for a customer fails. The `Payments Service` makes a request to the `predict module` to get the next best time to charge.
2.  **Signal Retrieval**: The `predict module` collects the most recent usage and payment signals for the customer from **Edgestore**.
3.  **Prediction Request**: The collected signals are sent to the **Predict Service** via a gRPC call. The `Predict Service` encodes the signals into a feature dataframe.
4.  **Prediction Generation**: The model (a gradient boosted ranker) receives the features and returns the best-ranked time chunk for the next charge attempt. The model ranks one-hour chunks within a given window (e.g., 192 chunks for an 8-day window).
5.  **Response**: The prediction is sent back to the `predict module`, which returns the result to the `Billing Policy` component of the Payments Platform.
6.  **Logging**: The `predict module` logs the model's prediction and other relevant information for troubleshooting and analysis.
7.  **Scheduling**: The `Payments Service` receives the recommended charge time and schedules the next payment attempt, storing the schedule in **Edgestore**.
8.  **Iterative Process**: If a subsequent retry fails, this entire process is repeated. The model is called again to provide the next best time, continuing until the payment succeeds or the maximum renewal window is exhausted.

### 13. Monitoring

A multi-layered monitoring strategy is in place, with responsibility split between the Payments and Applied ML teams.

#### 13.1. Business metrics

- **Invoice Approval Rate**: The primary success metric.
- **Attempt Success Rate**: Tracks how quickly renewals are recovered.
- **Tooling**: **Superset** is used for monitoring business metrics.

#### 13.2. Model quality

These online metrics help diagnose model health in production.
- **Coverage**: The percentage of customers that receive a recommendation from the model.
- **Number of predictions made**: The volume of successful recommendations served without errors.
- **Prediction Latency**: The time taken for the model to generate a recommendation.
- **Tooling**: **Grafana** and **Vortex** are used for monitoring model and infrastructure metrics.

#### 13.3. Infrastructure monitoring

- **Data Pipeline Health**: Freshness and delays in feature data pipelines.
- **Service Health**: Availability and latency of the **Predict Service**.
- **Storage Health**: Availability of **EdgeStore**.
- **Tooling**: **Grafana** and **Vortex**.

### 14. Operations

#### 14.1. Automation and retraining

- Data collection is automated via daily Airflow jobs.
- The ML system is designed to be retrained to adapt to new patterns, in contrast to the static rule-based system whose performance would decay.

#### 14.2. On-call and incident response

- Responsibility for monitoring is split between the Payments engineering team and the Applied Machine Learning team.
- Troubleshooting guides and clear escalation paths are established to help on-call engineers debug issues.
- The ML team spent time training the Payments engineering team on how the system works and how to interpret model results to ensure smooth collaboration.