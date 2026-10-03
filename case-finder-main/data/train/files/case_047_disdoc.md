**Company**: Linkedin
**Title**: Ocelot: Scaling observational causal inference at LinkedIn
**Technology area**: Predictive ML
**Source URL**: https://engineering.linkedin.com/blog/2022/ocelot--scaling-observational-causal-inference-at-linkedin
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The core business need is to understand the causal impact of product changes on key metrics related to member and customer experiences at LinkedIn. While A/B testing is the ideal method for establishing causality, it is often infeasible or too costly. The problem is to estimate causal effects from observational data where treatment is not randomly assigned.

#### 1.2. Relevance & reasons

A/B testing cannot be used in several important scenarios:
*   **Brand Marketing Campaigns**: It is not possible to randomize exposures to TV, billboard, or radio ads at the user level.
*   **Bugs or Downtime**: It is undesirable to run experiments that intentionally randomize bad experiences for users. However, quantifying the impact of these events is crucial for prioritizing infrastructure resources.
*   **Exogenous Shocks**: It is impossible to randomize the impact of external events like government policy changes or economic downturns on the labor marketplace.

In these cases, simply observing the correlation between a change and a metric is misleading due to confounding variables. Observational causal inference provides a collection of methods to estimate treatment effects by adjusting for these confounders.

#### 1.3. Expectations

The system, named Ocelot, is expected to make observational causal inference more accessible, easier to use, and faster to execute for data scientists at LinkedIn. It should enable users, even those who are not experts in causal inference, to run complex causal studies with no coding effort. The platform must deliver reliable estimates of causal relationships along with robustness checks to ensure a high standard of rigor for product decision-making.

#### 1.4. Previous work

Before the Ocelot platform, conducting an observational causal study was a resource-intensive, ad-hoc process:
*   **Team**: It required a team of at least two data scientists: one experienced causal inference expert and one domain expert.
*   **Timeline**: A single study took up to six weeks to complete.
*   **Process**: The process involved manually designing the study, building custom data pipelines, writing ad-hoc modeling scripts, and then validating and analyzing the results.
*   **Throughput**: Due to the high cost, only 10-20 observational causal studies were produced in total before Ocelot's launch.

#### 1.5. Usage volumes and patterns

*   **User Base**: The platform serves a company with over 875 million members.
*   **Study Volume**: Since its launch in 2019, Ocelot has enabled more than 50 causal studies per year, a significant increase from the previous 10-20 total.
*   **User Profile**: The primary users are domain expert data scientists who can now run studies independently.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Democratization**: Make observational causal inference accessible to all data scientists, not just a few experts.
*   **Velocity**: Reduce the time to complete a thorough causal study from 6 weeks to less than one week. A simple study should be executable in a couple of hours.
*   **Scale**: Increase the number of causal studies conducted annually to over 50.
*   **Rigor & Reliability**: Ensure all studies meet a high standard by bundling automated robustness checks and implementing a mandatory peer-review process.
*   **Ease of Use**: Enable users to run complex studies through a guided UI with no coding required.
*   **Knowledge Sharing**: Create a centralized, searchable repository of past studies that can serve as templates and learning resources.

#### 2.2. Anti-goals

*   **Allowing Causal Claims from Flawed Studies**: The system explicitly prevents users from claiming a result is causal if automated robustness checks fail.
*   **Encouraging "P-hacking"**: The platform tracks the full execution history of a study, including all iterations, to discourage users from repeatedly tweaking parameters until a desired result is achieved.
*   **Replacing A/B Testing**: Observational causal inference is positioned as a complement to A/B testing for situations where randomization is not possible, not a replacement for it.

### 3. Risks and constraints

*   **Confounding**: The fundamental challenge is that treated and untreated groups may differ systematically. The methods aim to adjust for *observed* confounders, but *unobserved* confounders can still bias the results.
*   **Unverifiable Assumptions**: Causal inference methods rely on assumptions that are often impossible to verify (e.g., no unobserved confounding for the doubly robust method, the exclusion restriction for instrumental variables).
*   **Study Misconfiguration**: Incorrectly setting up the time periods for covariates, treatments, and outcome metrics is an "easy mistake" that can invalidate the entire study. For a Fixed Effect Model (FEM) with four time periods, this can involve 24 different dates.
*   **Misinterpretation of Results**: Users might misinterpret estimates or overstate their certainty. This is mitigated by the mandatory review committee.
*   **Data Scale**: Processing and joining data for 875M+ members with hundreds of potential confounders is a significant data engineering challenge.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The primary output of the system is the **treatment effect estimate**, which quantifies the causal impact of a treatment on an outcome metric. The reliability of this estimate is assessed via several robustness checks:
*   **A/A Test**: In a constructed scenario where the true treatment effect is zero, this test checks if the estimated effect is statistically significantly different from zero. A significant result indicates a flawed study design.
*   **Rerandomization Test**: Mentioned as an automated robustness check.
*   **Coverage Checks**: Mentioned as an automated robustness check.

#### 4.2. Online/business metrics

The system is used to measure the causal impact on any key business metric. An example provided is "Sessions". The user defines the output metrics to be measured in the study configuration.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Primary Data**: Large-scale member data from LinkedIn's data ecosystem.
*   **Feature Data**: The system is integrated with Feathr, LinkedIn's internal feature store, to access covariates (confounders).

#### 5.2. Labeling strategy

Treatment and control group assignments are based on observed user status, not random assignment. The user defines the control/treatment labels and the time periods over which they apply within the Ocelot UI.

#### 5.3. Available metadata

The system uses covariates to adjust for confounding.
*   A pre-defined **standard covariate set** is available, containing more than 200 commonly used covariates curated by domain experts.
*   An example covariate is `macrosessions_sum_7d` (session count in the previous week).
*   Users can select covariates by name from the UI.

#### 5.4. Data quality issues and cleaning

The main data quality issue is confounding. The platform's data preparation pipelines are designed to mitigate this by correctly joining and aligning user data with a rich set of covariates based on precise temporal definitions. The UI layer includes validation to prevent date misconfigurations.

#### 5.5. ETL

Ocelot includes a fully integrated data pipeline component ("Ocelot pipelines") that handles all data preparation.
*   **Technology**: The pipelines consist of Java jobs, Spark jobs, and R jobs running on Azkaban, LinkedIn's open-source workflow manager.
*   **Functionality**: The pipelines prepare the modeling data according to the user's configuration. This includes joining large-scale member data with selected covariates from Feathr and handling complex date logic for temporal models.
*   **Optimization**: The Spark jobs are fine-tuned to reduce data preparation time and failure rates when handling massive datasets.

### 6. Validation schema

Validation in Ocelot focuses on ensuring the robustness and reliability of the causal estimate, rather than traditional model validation.

*   **Automated Robustness Checks**: The platform automatically runs a suite of checks alongside every causal analysis. These include:
    *   **A/A Test**: The primary check to validate the study design's ability to account for confounding.
    *   **Rerandomization Test**
    *   **Coverage Checks**
    *   If these checks fail, the user is not permitted to claim the results are causal.

*   **Manual Peer Review**: A central review committee must vet all studies before their results can be interpreted as causal.
    *   The committee meets weekly to discuss study designs and results.
    *   It is composed of members from a horizontal Data Science Applied Research team (deep technical expertise) and data scientists from product verticals (domain knowledge).
    *   The committee assesses the reasonableness of the method's underlying assumptions in the context of the study.

### 7. Baseline solution

The baseline was the pre-Ocelot, ad-hoc process for conducting observational causal studies.
*   **Methodology**: It involved manual data pipeline construction using ad-hoc scripts.
*   **Efficiency**: The process took up to 6 weeks for a single study.
*   **Expertise**: It required a dedicated team including a causal inference expert and a domain expert.
*   **Throughput**: This process was not scalable, resulting in only 10-20 studies being completed in total.
*   A more simplistic baseline is the raw metric difference between treated and untreated groups, which the article explicitly identifies as misleading and insufficient due to confounding.

### 8. Errors and their analysis

*   **Data Preparation Errors**:
    *   **Cause**: Misconfiguration of the 24+ dates required for a typical Fixed Effect Model.
    *   **Mitigation**: The Ocelot UI provides a guided form with built-in validation to prevent date overlaps and other configuration errors. The automated pipeline handles the complex data joins, removing the risk of manual error.

*   **Methodology Errors**:
    *   **Cause**: The chosen causal method fails to adequately adjust for confounding, leading to a biased estimate.
    *   **Diagnosis**: This is detected by the failure of automated robustness checks, particularly the A/A test. A failed check signals that the study design is flawed and the results are untrustworthy.

*   **Interpretation Errors**:
    *   **Cause**: Overstating the certainty of an estimate, ignoring unverifiable assumptions, or claiming causality despite failed robustness checks.
    *   **Mitigation**: The mandatory central review committee provides expert oversight. The platform also captures study history to prevent p-hacking and requires study owners to acknowledge underlying assumptions when presenting results.

### 9. Training pipelines

The system uses "Ocelot pipelines" for an end-to-end analytical workflow. This is not a traditional "training" pipeline but an on-demand analysis pipeline.

*   **Tooling**:
    *   **Workflow Orchestration**: Azkaban.
    *   **Processing Engines**: Java, Spark (fine-tuned for performance), and R jobs.
    *   **Feature Management**: Integrated with the Feathr feature store.
    *   **User Interface**: Ocelot web app (UI + web services).

*   **Pipeline Stages**: The pipeline is triggered by a user in the UI and automates the following:
    1.  **Data Preparation**: Fetches and joins member data with specified covariates from Feathr, respecting the complex date configurations for the chosen method.
    2.  **Causal Modeling**: Executes one of the available causal methods based on user selection.
    3.  **Robustness Checking**: Automatically runs A/A tests and other checks on the results.
    4.  **Reporting**: Generates a detailed report in the UI.

*   **CI/CD**: [NO INFO]

### 10. Features

In the context of Ocelot, "features" are the **covariates** or **confounders** used to adjust for selection bias.

*   **Feature Categories**: The platform supports a wide range of covariates that may influence both treatment assignment and outcomes. An example is user activity metrics like `macrosessions_sum_7d`.
*   **Feature Selection**:
    *   Users select covariates from a list in the UI.
    *   A **standard covariate set** of over 200 commonly used features is pre-defined by domain experts to simplify setup and promote best practices.
*   **Feature Computation**: The platform is integrated with the **Feathr** feature store. Users select features by name, and the Ocelot pipeline handles the logic for fetching, joining, and aggregating these features according to the specific date requirements of the study.
*   **Feature Importance**: [NO INFO]

### 11. Measuring results

*   **Offline Evaluation**: The primary result is the **treatment effect estimate**. Its validity is evaluated through the automated robustness checks (A/A test, etc.). Passing these checks increases confidence in the result.
*   **A/B test design**: Not applicable, as Ocelot is designed for scenarios where A/B testing is not an option.
*   **Reporting**: The Ocelot UI serves as the reporting dashboard. It presents:
    *   A detailed report with key results (treatment effect estimates).
    *   The pass/fail status of all automated robustness checks.
    *   Data visualizations to aid in study configuration and interpretation.
    *   Searchable metadata like study description, goals, and tags.
    *   A complete iteration history for each analysis to ensure transparency.
*   **Decision Criteria**: A treatment effect can be claimed as causal **only if** the study passes the automated robustness checks AND is approved by the central review committee.

### 12. Integration and Serving

Ocelot is an internal, offline analytics platform, not a real-time serving system.

*   **API design**: The system is a web application composed of the "Ocelot UI" and "Ocelot web services". Users interact with it via a guided web form. There is no public-facing serving API.
*   **Infrastructure**:
    *   **Frontend/Backend**: Ocelot web app.
    *   **Data Processing**: A backend pipeline of Java, Spark, and R jobs orchestrated by Azkaban.
*   **SLAs, latency budgets, and fallback strategies**:
    *   **Latency**: The key "latency" is the time-to-result for a study. Ocelot reduced this from 6 weeks to under 1 week for a thorough study, and a few hours for a simple one.
    *   **Fallback Strategy**: If a chosen causal method fails its robustness checks, the primary fallback is for the user to reconsider their study design, select different covariates, or try one of the other available methods on the platform.

### 13. Monitoring

*   **Data Quality and Schema Checks**: The UI layer performs validation to prevent misconfiguration of study parameters, such as dates for metrics and covariates.
*   **Model Quality and Prediction Drift**: "Model quality" is monitored with every run via the suite of automated robustness checks (e.g., A/A test). A failed check is an immediate signal of a quality issue with the analysis.
*   **Input/Target Drift**: The entire purpose of the system is to handle the inherent "drift" (i.e., systematic differences) between the observed treatment and control groups.
*   **Engineering Metrics**: The team monitors pipeline performance, having fine-tuned Spark jobs to reduce data preparation time and job failure rates.
*   **Alerting**: [NO INFO] (but likely tied to Azkaban job failures).

### 14. Operations

*   **Retraining Cadence**: Not applicable. Causal studies are executed on-demand by data scientists to answer specific business questions.
*   **Operational Procedures**:
    1.  **Initiation**: A data scientist logs into the Ocelot UI.
    2.  **Configuration**: They select a causal method and fill out a guided form to define the study (metrics, labels, covariates, dates). They can clone past analyses to start.
    3.  **Execution**: The user executes the analysis with a button click, which triggers the backend Azkaban workflow.
    4.  **Iteration**: The user reviews results and can iterate on the design. All iterations are tracked.
    5.  **Review**: Once the study is finalized, the user submits it to the central committee for review and approval.
*   **Ownership**:
    *   **Study Owners**: Domain expert data scientists.
    *   **Platform Owners**: The horizontal Data Science Applied Research team builds and maintains Ocelot.
    *   **Governance**: The central review committee, with members from both horizontal and product teams, is responsible for vetting all studies.
*   **Knowledge Management**: The platform features high-quality, peer-reviewed studies as templates. All studies are captured with searchable descriptions and tags to facilitate knowledge sharing.