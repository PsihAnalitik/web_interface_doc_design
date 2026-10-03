**Company**: Lyft
**Title**: Causal Forecasting at Lyft (Part 1)
**Technology area**: Predictive ML
**Source URL**: https://eng.lyft.com/causal-forecasting-at-lyft-part-1-14cca6ff3d6d
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The core business problem is the efficient management of Lyft's two-sided marketplace, which involves balancing driver supply and rider demand. This requires making strategic decisions about market management tools like driver bonuses, rider coupons, and pricing to provide affordable rides with low ETAs under changing market conditions.

The system, referred to as Lyft's "Causal Forecasting System", is designed to support these strategic decisions. It is used by internal product-focused teams (e.g., driver bonuses, rider coupons, pricing) to understand the downstream consequences of their actions and to set their operational inputs, such as weekly spending budgets.

#### 1.2. Relevance & reasons

Making smart, forward-looking decisions for large capital allocation is critical. A purely correlational model is insufficient because historical data is heavily confounded by Lyft's own past policy decisions. For example, a simple correlation might incorrectly suggest that decreasing driver incentive budgets increases driver hours. To make effective planning decisions, it is essential to sift out the true causal relationships between policy actions and business outcomes.

The system aims to create a "consensus view" of the business, enabling intelligent, organization-level decisions that go beyond the local optimizations of individual teams.

#### 1.3. Expectations

The system is expected to perform two primary tasks:
1.  **Forecasting**: Build a model that accurately forecasts key business metrics (V₁, V₂, …, Vₖ) such as ride counts and revenue, given a set of controllable policy variables (C₁, C₂, …, Cₗ) like incentive budgets or the rate card.
2.  **Optimization**: Use the model to determine the optimal values for the policy variables that maximize a specific business objective, such as total rides under a revenue constraint.

The output of this system directly drives large capital allocation decisions.

#### 1.4. Previous work

The article implies that previous approaches relied on correlational models. These were found to be inadequate for planning and decision-making, as they could learn spurious relationships from confounded historical data and lead to incorrect conclusions about the impact of policy changes.

#### 1.5. Usage volumes and patterns

The system is used for strategic planning and making "large capital allocating decisions." It is not a real-time serving system but a tool for scenario analysis and optimization, accessed via UIs by internal decision-makers.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Causal Validity**: The model must be causally valid, meaning it accurately represents the differential relationships between policy inputs and business outcomes, allowing it to be used for planning and "what-if" analysis.
*   **Predictive Accuracy**: The model must accurately forecast key business metrics by fitting well to historical data.
*   **Decision Optimization**: The system must be able to find optimal settings for policy variables to achieve a specific business goal (e.g., maximize rides).
*   **Modularity and Scalability**: The system should support a "divide-and-conquer" strategy, allowing different data science teams to model their specific domains independently. These sub-models are then stitched together into a single, comprehensive model of the business.
*   **Interpretability**: The model structure, represented as a Directed Acyclic Graph (DAG), should communicate the functioning of the business and encode a consensus view.

#### 2.2. Anti-goals

*   **Purely Correlational Modeling**: The system must not be a merely correlational model that simply fits historical patterns without capturing causal structure. Such a model is explicitly identified as dangerous for planning.

### 3. Risks and constraints

*   **Data Confounding**: A major constraint is that the historical data is "heavily confounded by our previous decisions." This makes it difficult to learn causal effects from observational data alone.
*   **Incorrect Causal Assumptions**: The model's validity depends on the correctness of the underlying causal assumptions encoded in the DAG. An incorrect graph structure would lead to flawed forecasts and optimizations.
*   **Model Misspecification**: A sub-model might fail to correctly capture the functional relationship between its inputs and outputs, even if the causal graph is correct. The article gives an example of a correlational model predicting that decreasing driver incentive budget increases driver hours, which is "obviously wrong."
*   **Organizational Complexity**: The system needs to integrate models from various product-focused teams, which requires robust software and processes to ensure seamless integration and a consistent "consensus view."

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The article mentions the need for "similarly accurate predictions" compared to baseline models and the ability to "fit historical data," but does not specify the exact offline evaluation metrics (e.g., MAPE, RMSE). The primary measure of offline quality is the model's ability to match experimentally determined causal relationships (e.g., cost curves) while also fitting observational data.

#### 4.2. Online/business metrics

The system forecasts and optimizes for key business metrics (V₁, V₂, …, Vₖ). Examples include:
*   Counts of riders opening the Lyft app ("sessions")
*   Ride counts
*   Revenue
*   Revenue-per-ride

An example optimization objective is given: `maximize "total rides subject to a revenue-per-ride constraint"`. This is expressed as optimizing a scalar function `f(V₁, V₂, …, Vₖ)`.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Observational Data**: Internal time-series data on business metrics and policy variables.
    *   **Policy Variables (Controls)**: Driver incentive budgets, rider coupons, pricing/rate card.
    *   **Business Metrics (Outcomes)**: Sessions, conversion rates, rides, revenue, driver hours.
*   **Experimental Data**: Results from experiments are used to determine the functional form of causal relationships. A key example is using an experimentally determined "cost curve" that defines the relationship between driver incentive budget and driver hours.

#### 5.2. Labeling strategy

The business metrics (e.g., `rides`, `revenue`) serve as the target variables (labels) for the forecasting tasks. The causal relationships themselves are validated and quantified using data from controlled experiments.

#### 5.3. Data quality issues

The primary data quality issue is **confounding**, where the observed relationship between a policy variable and an outcome is distorted by the influence of other factors, including past policy decisions themselves.

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

The article does not describe a standard train/validation/test split strategy. Instead, validation appears to be a two-part process:
1.  **Observational Fit**: The model must fit historical observational data accurately.
2.  **Causal Fit**: The model's predicted response to changes in policy variables must match empirical relationships derived from experiments (e.g., cost curves).

The article notes that a model often must "trade off how well it matches observations vs experiments."

### 7. Baseline solution

A **correlational model** is used as a baseline to demonstrate the need for a causal approach.
*   **Example Implementation**: For predicting driver hours from driver incentive budget, a baseline model is described as one that "smooths the input budget and applies a polynomial regression."
*   **Performance**: This baseline model learns a spurious negative correlation from the confounded historical data. When used for planning (i.e., evaluating the effect of changing the budget), it incorrectly suggests that decreasing the budget would increase driver hours, making it unsuitable for decision-making.

### 8. Errors and their analysis

The primary type of error analyzed is the model learning an incorrect causal relationship.
*   **Error Analysis Technique**: The analysis involves examining the model's "differential relationship." This is done by holding all other inputs constant for a specific date, varying a single policy variable (e.g., driver incentive budget), and observing the model's predicted change in the outcome (e.g., "incremental driver hours").
*   **Identified Error**: The correlational baseline model produced a nonsensical differential relationship, showing that for a budget above ~$60K, driver hours could be increased by *decreasing* the budget.
*   **Mitigation**: The solution is to build a model that explicitly incorporates and obeys the experimentally determined causal relationship (the "cost curve"). The example model uses the cost curve directly to model the impact of budget on driver hours and then uses a "smoothly evolving moving average to model the residual." This is described as being analogous to an ARIMAX model.

### 9. Training pipelines

#### 9.1. Tooling

*   **Core Library**: **PyTorch** is used to develop the large, composite model.
*   **Modeling Paradigm**: The system is built on a "divide-and-conquer" strategy where individual teams model their domains. The software (to be detailed in a future post) is designed to enable "independent modeling yet a seamless integration of those models."

#### 9.2. Process

1.  **Decomposition**: The overall business problem is decomposed into smaller modeling tasks based on a Directed Acyclic Graph (DAG) representing causal assumptions.
2.  **Parallel Modeling**: Individual product-focused data science teams model the causal relationships within their domain (e.g., the driver bonus team models the effect of budget on driver hours).
3.  **Model Integration**: The individual sub-models are "stitched together" to form a single large, comprehensive causal model that represents the entire business.

### 10. Features

#### 10.1. Feature categories

Features in this system are the variables in the causal DAG. They can be categorized as:
*   **Policy Variables (Control Variables)**: These are the inputs to the overall model, representing decisions Lyft can make.
    *   Driver incentive budget
    *   Rider coupons
    *   Pricing / Rate Card (cost per minute and per mile)
*   **Intermediate Business Metrics**: These are nodes in the DAG that are outputs of some models and inputs to others.
    *   Sessions
    *   Conversion rate
    *   Driver hours

#### 10.2. Feature selection

Feature selection is implicitly defined by the structure of the causal DAG. For each variable (node) to be predicted, its features are its causal parents in the graph. The DAG itself is constructed based on a combination of business knowledge and experimental evidence.

### 11. Measuring results

#### 11.1. Offline evaluation

Offline evaluation is based on a model's ability to satisfy two criteria simultaneously:
1.  **Predictive Accuracy**: The model must accurately fit historical observational data.
2.  **Causal Fidelity**: The model must reproduce known causal relationships derived from experiments (e.g., cost curves).

The article notes that complex models are more capable of matching both observations and experimental results than simpler ones.

#### 11.2. A/B test design

A/B tests (experiments) are not used to validate the final model's output. Instead, they are a critical **input** to the modeling process. The results of experiments are used to "inform the functional relationship between policy decisions and outcomes," providing ground truth for the causal links that the model must learn.

#### 11.3. Reporting

The system includes UIs that allow decision-makers to interact with the model directly. This enables:
*   **Scenario Planning**: Evaluating the trade-offs between different strategies (e.g., "balanced vs aggressive growth strategy") by forecasting outcomes under different sets of policy decisions.
*   **Optimization**: The model is used to solve for the optimal policy variables that maximize a given objective function.

### 12. Integration and Serving

#### 12.1. API design and serving pattern

The system is a **planning and optimization tool**, not a real-time serving system. It is used for offline analysis to inform strategic decisions.
*   **Interaction Model**: Users interact with the system via UIs to run "what-if" scenarios and optimizations.
*   **Output**: The output is a "plan," which consists of forecasts for key metrics conditional on a chosen set of policy decisions.

#### 12.2. Infrastructure

*   **ML Framework**: PyTorch.
*   **Architecture**: A composite model formed by stitching together smaller, independently developed models. The software enabling this integration is mentioned but not detailed.

#### 12.3. SLAs and fallback strategies

[NO INFO]

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Retraining cadence

[NO INFO]

#### 14.2. Ownership

The modeling process is decentralized.
*   **Sub-model Ownership**: Product-focused teams (e.g., driver bonuses team, rider coupons team) are responsible for modeling the metrics and causal relationships "within their control."
*   **System Ownership**: A central system [inferred] is responsible for integrating these sub-models into the comprehensive "Causal Forecasting System."

#### 14.3. Incident response and rollback procedures

[NO INFO]

#### 14.4. Non-engineering considerations

The system is designed to be used directly by business decision-makers for high-stakes choices. It provides UIs for scenario evaluation and optimization, translating complex model outputs into actionable business plans. The entire framework is designed to create a "consensus view of our business" that can be used to align different teams around a common set of assumptions and goals.