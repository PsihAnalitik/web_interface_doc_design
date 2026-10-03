- Company: Netflix
- Title: Metrics Projection for Growth A/B Tests
- Technology area: Predictive ML
- Source URL: https://netflixtechblog.com/round-2-a-survey-of-causal-inference-applications-at-netflix-fd78328ee0bb
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The system is designed to estimate the long-term business impact of new product features tested via A/B experiments at Netflix. When a new feature is launched, its annualized incremental impact on the business needs to be estimated from short-term A/B test results.

The core problem is that A/B tests are often run for a limited duration (e.g., allocating users for one month and monitoring for two billing periods), but the business needs to understand the impact over a full year. This creates two specific missing data challenges:
1.  **Unobserved billing periods:** For cohorts that participated in the test, their behavior (and thus the treatment effect) is unknown for future billing periods beyond the observation window.
2.  **Unobserved signup cohorts:** The test only captures cohorts that sign up during the experiment's duration. The impact on cohorts signing up in the subsequent months of the year is unknown.

#### 1.2. Relevance & reasons

Historically, the estimation of annualized impact was a manual process performed by Netflix's Finance, Strategy, & Analytics (FS&A) partners. This process involved manually forecasting signups, retention probabilities, and cumulative revenue for each test cell over a one-year horizon. This manual workflow was described as "repetitive and time consuming." The new system aims to provide a "faster, automated approach" to deliver these crucial business estimates.

#### 1.3. Expectations

The primary expectation is for the system to provide "quicker and more accurate estimates" of the long-term value that new product features deliver to members. The output should be an estimate of the annualized incremental impact on key business metrics.

#### 1.4. Previous work

The previous solution was a manual forecasting process conducted by the Finance, Strategy, & Analytics (FS&A) team. For each A/B test cell, they would manually project signups, retention, and revenue for a one-year horizon using monthly cohorts.

#### 1.5. Usage volumes and patterns

The system is used to analyze A/B tests for new product features. A typical usage pattern involves an A/B test that allocates users for one month and monitors results for only two billing periods. The system then projects the impact from this limited data to a full one-year horizon.

### 2. Goals and anti-goals

#### 2.1. Goals

*   Automate the estimation of the annualized incremental impact of product features from short-term A/B tests.
*   Reduce the time required to generate long-term impact estimates compared to the previous manual process.
*   Improve the accuracy of long-term impact forecasts.
*   Estimate the treatment effect on key business metrics such as signups, retention probabilities, and cumulative revenue over a one-year horizon.

#### 2.2. Anti-goals

[NO INFO]

### 3. Risks and constraints

*   **Constraint:** A/B tests are often short-term, providing limited observational data for long-term projections. For example, a test might only run for one month and collect data for two billing cycles.
*   **Risk:** The accuracy of the projections depends on key assumptions that may not hold true.
    *   **Surrogate Assumption:** The model assumes that the causal path from the treatment to the outcome (Revenue) goes through the surrogate metric of retention.
    *   **Transportability Assumption:** The model assumes that the treatment effect observed in the first cohort of an experiment is the same for all subsequent, unobserved signup cohorts throughout the year. The article notes this is a testable assumption if long-running A/B tests are available.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The system's projections are empirically validated against two benchmarks:
*   **Long-running A/B tests:** Comparing the system's annualized projections with the actual, observed long-term results from experiments that were allowed to run for a longer duration.
*   **Prior FS&A results:** Comparing the system's automated estimates with the historical manual forecasts produced by the FS&A team.

#### 4.2. Online/business metrics

The system projects the annualized incremental impact (Treatment Effect, TE) on the following business metrics:
*   Signups
*   Retention probabilities (by monthly cohort)
*   Cumulative revenue

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The primary data source is the results from A/B tests on product features. Specifically, the system uses:
*   Observed treatment effects (TEs) for each billing period within the test's observation window. In the provided example, this corresponds to `𝜏.cohort1,period1` and `𝜏.cohort1,period2`.
*   Data from a proprietary Netflix Retention Model, which is used as part of the projection methodology.

#### 5.2. Labeling strategy

The "labels" for this system are the observed treatment effects on retention, measured directly from the A/B test for the initial cohorts and billing periods.

#### 5.3. Available metadata

*   Cohort identifiers (e.g., monthly signup cohort).
*   Billing period identifiers.

#### 5.4. Data quality issues

The primary data issue is "missingness" by design, which the system is built to address:
*   **Unobserved billing periods:** Treatment effects for periods `j = 3…12` are missing for the first cohort.
*   **Unobserved sign up cohorts:** Both the size and the treatment effects for cohorts `i = 2…12` are missing.

#### 5.5. ETL

[NO INFO]

### 6. Validation schema

The validation schema is empirical and retrospective.
*   **Comparison to Ground Truth:** Projections from the model are compared against the actual results of historical "long-running AB tests" where the full year of data is available.
*   **Comparison to Baseline:** Projections are also compared against the "prior results" from the manual forecasting process performed by the FS&A partners.

### 7. Baseline solution

The baseline solution was the existing manual process performed by the Finance, Strategy, & Analytics (FS&A) team. This involved analysts manually forecasting signups, retention probabilities, and cumulative revenue for each cell of an A/B test to project the impact over a one-year horizon. This process was effective but "repetitive and time consuming."

### 8. Errors and their analysis

The system's methodology is designed to address two primary sources of error stemming from missing data.

*   **Error from unobserved billing periods:** To project treatment effects for future billing periods for an observed cohort (e.g., `𝜏.1,j` for `j = 3…12`), the system uses a **surrogate index approach**. It leverages a proprietary Retention Model and the short-term observed treatment effects (e.g., `𝜏.1,2`) to estimate the decay or evolution of the treatment effect over time. This relies on the assumption that retention is a valid surrogate for long-term revenue.

*   **Error from unobserved signup cohorts:** To estimate the impact on future, unobserved cohorts (e.g., cohorts `i = 2…12`), the system assumes **transportability**. This means the billing-period treatment effects observed for the first cohort are assumed to be the same for all subsequent cohorts. The article notes that this is a testable assumption using data from long-running A/B tests, providing a mechanism to validate and potentially correct for this source of error.

### 9. Training pipelines

[NO INFO]

*Note: The system is described as an estimation framework rather than a traditional ML model that is trained. It uses a pre-existing "proprietary Retention Model" as a component, but the training pipeline for that model is not detailed.*

### 10. Features

The inputs to the projection model are not traditional ML features but rather statistical estimates and model outputs:
*   **Observed Treatment Effects:** Short-term treatment effects on retention measured from an A/B test (e.g., `𝜏.1,1`, `𝜏.1,2`).
*   **Retention Model Output:** The system leverages a proprietary Retention Model to inform the projection of treatment effects over longer time horizons.

The final output is the estimated annualized impact, which is calculated by summing the observed and projected treatment effects for all cohorts over a 12-month period.

### 11. Measuring results

#### 11.1. Offline evaluation methodology

The system's performance is measured by comparing its automated projections against:
1.  The actual, observed outcomes from historical long-running A/B tests.
2.  The historical forecasts generated by the manual FS&A process.

The goal is to demonstrate that the automated approach is both "quicker and more accurate."

#### 11.2. A/B test design

This system is an analysis tool for A/B tests, not an A/B test itself. It is designed to work with input from A/B tests that may have short observation windows, such as allocating users for one month and monitoring for two billing periods.

#### 11.3. Reporting format

The final output is an estimate of the "annualized incremental impact on the business," which includes metrics like signups, retention, and cumulative revenue.

### 12. Integration and Serving

#### 12.1. API design

The system is an "automated approach" that replaces a manual workflow. This implies it is an offline, batch processing system that likely runs after an A/B test has concluded its initial observation period. It is not a real-time serving system.

#### 12.2. Infrastructure

[NO INFO]

#### 12.3. SLAs

The primary goal is to be "faster" than the previous manual process. No specific latency budget or SLA is mentioned.

#### 12.4. Fallback strategies

The implicit fallback is to revert to the previous manual forecasting process performed by the FS&A team.

### 13. Monitoring

The article mentions one form of ongoing validation: the "transportability" assumption (that treatment effects are consistent across cohorts) is a "testable assumption" using long-running A/B tests. This suggests a periodic review process to ensure the model's core assumptions remain valid. No other details on monitoring for data quality, model drift, or engineering metrics are provided.

### 14. Operations

#### 14.1. Retraining cadence

The proprietary Retention Model used by the system would have its own retraining cadence, which is not described. The projection framework itself is an estimation method and does not appear to be "retrained" in a conventional sense.

#### 14.2. Ownership

The system was developed as a collaboration between Data Science and Engineering and the Finance, Strategy, & Analytics (FS&A) teams.

#### 14.3. Incident response

[NO INFO]