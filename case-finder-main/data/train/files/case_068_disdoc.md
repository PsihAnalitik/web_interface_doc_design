Here is the ML system design document, transformed from the provided source.

---
- **Company**: Shopify
- **Title**: Monte Carlo Simulations: Separating Signal from Noise in Sampled Success Metrics
- **Technology area**: Predictive ML
- **Source URL**: https://shopify.engineering/monte-carlo-simulations-sampled-success-metrics
- **Content type**: article
---

### 1. Problem definition

#### 1.1. Origin

Shopify aims to continuously improve the quality of the apps available in its App Store. The App Store hosts over 8,000 apps, which must meet over 200 minimum requirements focused on security, functionality, and ease of use. The core business question is, "How good are our apps?". This is translated into a quantitative problem: "How many requirements does the average app violate?".

#### 1.2. Relevance & reasons

It is too expensive and time-consuming to audit every one of the 8,000+ apps against all requirements on a continuous basis. Therefore, Shopify relies on a sampled success metric to track the effectiveness of its various manual and automated app review processes. A key challenge is that metrics derived from samples are subject to random noise. It is difficult to distinguish a true trend (signal) from random fluctuations (noise) when looking at the metric in isolation. This makes it hard to confidently assess the impact of quality improvement initiatives.

#### 1.3. Expectations

The system must provide a reliable method to understand the variability of the sampled success metric. This will allow stakeholders to:
- Determine the necessary sample size (number of app audits per month) to achieve a desired level of confidence in the metric's trend.
- Understand the trade-off between the cost of data collection (more audits) and the certainty of the metric.
- Make informed decisions based on the metric, accounting for its inherent uncertainty.
- Communicate complex statistical concepts to non-technical stakeholders in simple terms (e.g., "percentage of certainty").

#### 1.4. Previous work

The standard approach is to directly measure a metric. When that is not feasible, one might track a sampled metric over time. However, this can be misleading if the sampling noise is not properly understood. The Monte Carlo simulation is proposed as a more robust method compared to simply observing the raw sampled metric trend.

#### 1.5. Usage volumes and patterns

- **Population size**: Over 8,000 apps in the Shopify App Store.
- **Measurement cadence**: The success metric is tracked on a monthly basis to evaluate trends over time.

### 2. Goals and anti-goals

#### 2.1. Goals

- **Primary Goal**: To quantify the relationship between sample size (number of monthly audits) and the ability to reliably detect trends in the underlying app quality.
- **Secondary Goal**: To create a framework for making informed, data-driven decisions about the resources allocated to app auditing.
- **Communication Goal**: To translate statistical uncertainty into clear business trade-offs for stakeholders (e.g., cost of additional audits vs. gain in measurement certainty).

#### 2.2. Anti-goals

- **Anti-goal**: Making decisions based on single, noisy data points from the sampled metric without understanding the range of potential random variation.
- **Anti-goal**: Over-investing in data collection (audits) without a clear understanding of the marginal gain in certainty.

### 3. Risks and constraints

#### 3.1. Risks

- **Misinterpretation of Noise**: A primary risk is misinterpreting a random fluctuation in the sampled metric as a real change in app quality, leading to incorrect conclusions about the effectiveness of review processes.
- **Incorrect Assumptions**: The simulation's validity depends on the assumptions made about the underlying data distribution (e.g., that issue counts follow a Poisson distribution). If the real-world data behaves differently, the simulation results may be misleading.

#### 3.2. Constraints

- **Cost**: Auditing apps is expensive and time-consuming. The number of audits that can be performed each month is limited by budget and personnel. This is the primary constraint the simulation aims to optimize.
- **Information Asymmetry**: The true population metric (the average issue rate across all 8,000+ apps) is unknown and can only be estimated.

### 4. Metrics and loss functions

#### 4.1. Online/business metrics

- **Shop Issue Rate**: The primary sampled success metric. It is defined as "how many requirement violations merchants experience with the average installed app." It is calculated from a random sample of audited apps each month.

#### 4.2. Offline/simulation metrics

These are "metrics on metrics" used within the Monte Carlo simulation to describe the variability and reliability of the *Shop Issue Rate*.

- **Mean Absolute Percentage Error (MAPE)**: The percentage by which the simulated sampled *Shop Issue Rate* deviates from the true (simulated) underlying population rate each month. It measures the accuracy of the sample estimate.
- **1 month Decreases Observed (1mDO)**: The probability that the sampled metric will show a decrease month-over-month, given an assumed true decrease in the underlying population metric. This measures the metric's sensitivity to positive changes.
- **2 month Decreases Observed (2mDO)**: The probability of observing a decrease in the sampled metric over two consecutive months.
- **1 quarter Decreases Observed (1qDO)**: The probability of observing a decrease in the sampled metric over a full quarter.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The data is generated by internal app audits. Each month, a set of apps is randomly sampled from the Shopify App Store.

#### 5.2. Labeling

For each audited app, the "label" is the count of violations against Shopify's 200+ quality requirements. This is determined through a manual or automated review process.

#### 5.3. Data generation for simulation

The Monte Carlo simulation does not use historical data directly for training, but rather generates synthetic data based on assumptions derived from the real world. The number of issues per app is modeled using a **Poisson distribution**.

- The Poisson distribution is chosen because it models the sum of a collection of independent Bernoulli trials (where each requirement check is a trial).
- The distribution is defined by a single parameter, λ (lambda), which represents both the mean and the variance. In this context, λ is the average number of issues per app.

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

The system is not a predictive model trained on data, but a simulation framework. "Validation" is performed by running the simulation across a grid of parameters to understand the system's behavior under different plausible scenarios. This is analogous to a grid search for hyperparameter tuning.

The simulation is run for a one-year (12-month) period, with key parameters being varied:
- **Initial Mean (λ)**: The starting average number of issues per app (e.g., 10).
- **Underlying Trend**: The assumed true monthly percentage decrease in the issue rate due to improvement efforts (e.g., 2%, 5%, 7%).
- **Sample Size**: The number of apps audited per month (e.g., 50, 100, 150).
- **Iterations**: The number of simulation runs for each parameter set to get a stable estimate of the simulation metrics (e.g., 50 iterations).

### 7. Baseline solution

The baseline approach is to track the raw *Shop Issue Rate* over time and attempt to interpret its trend directly, without a formal model of its sampling variability. This is described as a "one-shot experiment" approach where each data point is evaluated in isolation, which can be misleading due to random noise.

### 8. Errors and their analysis

The "error" being analyzed is the sampling error: the difference between the measured *Shop Issue Rate* (from the sample) and the true, unobservable issue rate of the entire app population.

The entire Monte Carlo simulation is a method for analyzing this error:
- **Quantifying Error**: MAPE is used to measure the expected magnitude of the sampling error.
- **Trend Detection Errors**: The `XmDO` metrics analyze the probability of failing to detect a true underlying improvement (a form of Type II error). For example, a low `1mDO` means that even if app quality is truly improving, the sampled metric is unlikely to reflect that on a month-to-month basis.
- **Analysis via Simulation**: By running thousands of simulated time series, a distribution of possible outcomes is generated, allowing for a probabilistic understanding of the metric's behavior.

### 9. Training pipelines

This is a simulation pipeline, not a model training pipeline.

- **Tooling**: The implementation uses **Python** and **pandas**.
- **Pipeline Steps**:
    1. **Parameter Definition**: Define the grid of parameters to explore (initial mean, decrease rates, sample sizes).
    2. **Time Series Generation (`generate_time_series`)**: A core function that simulates one 12-month time series. For each month, it calculates the true population mean (λ) based on the assumed decrease rate, then draws `sample_size` random values from a Poisson(λ) distribution. The mean of these values becomes the sampled metric for that month.
    3. **Metric Calculation**: For each generated time series, calculate the simulation metrics (MAPE, 1mDO, 2mDO, 1qDO).
    4. **Iteration (`run_simulation`)**: A wrapper that runs the generation and calculation steps multiple times (e.g., 50 iterations) for a single set of parameters and averages the resulting simulation metrics to get a stable estimate.
    5. **Grid Search Execution**: An outer loop iterates through all combinations of parameters defined in step 1, running the simulation for each and storing the results.

### 10. Features

This system does not use features in the traditional ML sense. The simulation is parameterized by assumptions about the data generating process, not by features of individual data points. The single variable measured for each app is the **count of issues**.

### 11. Measuring results

#### 11.1. Offline evaluation

The results are the outputs of the simulation, typically presented in a table or series of plots. This output shows how the simulation metrics (MAPE, 1mDO, etc.) change as a function of the input parameters (especially sample size).

- **Example Result**: The simulation produces a table showing the outcomes for different sample sizes and underlying improvement rates. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_068/img_006.png`)
    - With 100 audits/month and a true 5% monthly improvement:
        - The sampled metric is expected to be off by 3.0% on average (MAPE = 0.03).
        - The sampled metric will show a decrease in 78% of months (1mDO = 0.78).
        - A decrease will be observed over two consecutive months 95% of the time (2mDO = 0.95).

The article also states a conclusion: "if we start at 10 average issues per audit, run 100 random audits per month, and decrease the underlying issue rate by 5 percent each month, we should see monthly decreases in our success metric 83 percent of the time." [Note: This 83% figure from the text differs from the 78% shown in the accompanying table for the same parameters].

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting

The simulation results are used to facilitate a conversation with stakeholders about the trade-off between cost and certainty. For example, the data science team can state that "an additional 50 audits per month would yield quantifiable improvements in certainty," allowing leadership to make an informed decision on whether the increased confidence is worth the additional expense.

### 12. Integration and Serving

This is an offline analysis and planning tool. It is not integrated into a production serving system.

- **API design**: [NO INFO]
- **Infrastructure**: [NO INFO]
- **SLAs, latency budgets, and fallback strategies**: [NO INFO]

### 13. Monitoring

The Monte Carlo simulation is a tool *for designing a monitoring strategy*. It does not require monitoring itself. By understanding the expected random variation of the *Shop Issue Rate*, the team can set better monitoring rules for that business metric. For example, instead of alerting on any monthly increase, they can define a threshold based on the simulated distribution of changes, reducing false alarms from random noise.

### 14. Operations

- **Retraining Cadence**: The simulation is not a model that requires regular retraining. It is a planning tool that should be re-run when business assumptions change significantly (e.g., a new program is expected to change the rate of improvement, or the budget for audits is reconsidered).
- **Ownership**: The analysis is conducted by data scientists.
- **Incident Response**: [NO INFO]
- **Stakeholder Reporting**: A key operational component is the regular communication of simulation insights to stakeholders to guide resource allocation and set expectations for metric-based goals.