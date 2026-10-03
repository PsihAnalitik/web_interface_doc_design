**Company**: Wayfair
**Title**: Share of Voice Optimization Engine
**Technology area**: Predictive ML
**Source URL**: https://www.aboutwayfair.com/careers/tech-blog/share-of-voice-optimization-engine
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

Wayfair's standard machine learning models for content personalization are trained on past customer behavior. This leads to an over-representation of historically popular product categories (e.g., sofas, rugs) and an under-representation of new or emerging categories where users have not yet had a chance to express preferences. This optimization for short-term engagement may not be optimal for long-term customer needs and company growth objectives, such as building awareness for new product lines like Kitchen Appliances.

The problem is to balance algorithmic personalization with strategic business goals. The business needs a mechanism to control the "Share of Voice" (SoV)—the proportion of customers who see messaging for a specific category—while still ensuring the messaging is shown to the most relevant customers possible.

#### 1.2. Relevance & reasons

The existing methods for controlling message exposure are crude and sub-optimal:
1.  **Promotions**: These override personalization entirely, showing all customers the same messages for a period.
2.  **Random Traffic Splitting**: This method achieves SoV targets by showing a message to a random subset of customers (e.g., a random 20% of users see a "Kitchen Essentials" banner). This approach meets the exposure targets but ignores individual customer interests and propensities.

The Share of Voice (SoV) Optimization Engine was created to address this gap. It aims to satisfy business-defined SoV targets while simultaneously maximizing the relevance of the message for each customer. For example, while ensuring 20% of traffic sees an "Appliance" message, the engine directs that message to the 20% of customers with the highest predicted propensity for appliances.

#### 1.3. Expectations

The system is expected to find the optimal assignment of messages to customers across various placements (e.g., on the homepage). This is framed as an optimization problem over a three-dimensional space of `Customer x Message x Placement`. The output should be a set of assignments that maximizes the cumulative, customer-level relevance of all displayed messages while adhering to SoV targets and other business constraints.

#### 1.4. Previous work

The primary baseline and previous method is **random traffic splitting** to achieve SoV targets. This involves assigning a random percentage of incoming traffic to see content for a specific category, without considering customer-level relevance. Another mentioned method is using **promotions**, which override personalization for all users.

#### 1.5. Usage volumes and patterns

The system is designed to handle a large decision space. The number of possible combinations of `[Customer, Message, Placement]` can be in the billions. A hypothetical example involves:
*   4 placements on the homepage.
*   50+ types of messages.
*   A large customer base.

The system runs as a daily batch process to generate assignments. These assignments are then served in real-time when a customer visits a page like the homepage.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Maximize Relevance**: The primary goal is to maximize the cumulative customer-level message relevance across all placements and customers.
*   **Meet Business Targets**: Strictly adhere to the Share of Voice (SoV) targets (upper and lower bounds) set by business stakeholders like marketing and brand teams.
*   **Enforce Constraints**: Satisfy various logical and business constraints, such as placement compatibility and message diversity per customer.
*   **Strategic Balance**: Enable a balance between short-term profit maximization (driven by pure personalization) and long-term business objectives (like growing awareness of new categories).

#### 2.2. Anti-goals

*   **Pure Personalization**: The system should not solely rely on personalization models that would ignore strategic SoV goals and under-serve new categories.
*   **Random Assignment**: The system should not use simple random traffic splitting, as this ignores customer propensity and leads to sub-optimal relevance.
*   **Ignoring Placement Value**: The system should not treat all placements as equal. It must account for the relative value (e.g., based on historical impressions) of different placements.

### 3. Risks and constraints

*   **Computational Complexity**: The optimization problem involves billions of decision variables (`Customer x Message x Placement`), making it computationally expensive and infeasible to solve for all customers at once. This is mitigated by batching and parallelizing the optimization process.
*   **Solver Dependency**: The solution relies on a third-party commercial solver, Gurobi.
*   **Upstream Model Dependency**: The engine's effectiveness is dependent on the quality of the scores from upstream propensity models.
*   **Business Constraints**: The optimization must operate within a set of strict business and logical constraints:
    *   **SoV Targets**: Each message category has a target SoV range (e.g., Appliances: 25%, Kitchen: 30%). (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_067/img_006.jpg`)
    *   **Placement x Message Applicability**: A binary matrix defines which messages are allowed to be shown in which placements. For example, a service message might be restricted to certain placements. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_067/img_007.jpg`)
    *   **Placement Population**: Every placement must be populated with a message. This is enforced as a mathematical constraint (row-wise sum must be 1).
    *   **Message Uniqueness per Customer**: A given customer should not see the same message across multiple placements. This is enforced as a column-wise constraint.
    *   **Other Nuanced Rules**: The system must be able to handle additional constraints, such as not showing credit card offers to existing cardholders.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The core of the system is a constrained optimization problem, not a traditional ML model. The objective function serves as the primary offline metric:
*   **Objective Function**: Maximize the cumulative customer-level message relevance. This is calculated as the sum of `relevance_score(customer, message) * placement_value(placement)` over all assigned `(customer, message, placement)` triplets.
    *   `relevance_score`: Provided by upstream propensity models.
    *   `placement_value`: A weight assigned to each placement based on its historical performance.

#### 4.2. Online/business metrics

While not explicitly stated, the value of placements is determined by historical online metrics such as **impressions, clicks, or orders**. This implies that A/B tests would measure the impact on these same metrics (e.g., Click-Through Rate, Conversion Rate, Revenue) against the baseline.

#### 4.3. Loss functions

This system does not use a loss function in the context of model training. It uses a mathematical optimization solver (Gurobi) to maximize an objective function subject to a set of linear constraints. The problem is defined as a variant of the **Generalized Assignment Problem**.

### 5. Data (Dataset)

The system synthesizes two categories of inputs: Business Inputs and Model Inputs. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_067/img_005.jpg`)

#### 5.1. Data sources

*   **Business Inputs**:
    *   **SoV Targets**: Upper and lower bound percentages for each message category, provided by the Wayfair Brand team and other business leaders.
    *   **Placement x Message Applicability Matrix**: A binary matrix indicating which messages can be shown on which placements.
    *   **Other Business/Logical Constraints**: A set of rules translated into mathematical constraints for the solver.

*   **Model Inputs**:
    *   **Customer x Message Relevancy Scores**: The engine consumes scores from a suite of existing propensity models. These models predict a customer's likelihood to purchase from a product class (e.g., Area Rugs, Fridges) or engage with a service (e.g., Registry). For a composite message like "Renovation," scores from multiple models (e.g., Flooring, Lighting, Vanity) can be combined.
    *   **Placement Value Matrix**: A matrix representing the relative value of each placement. This is derived from historical data on metrics like impressions, clicks, or orders.

#### 5.2. Labeling strategy

Not applicable. The system does not train on labeled data. It solves an optimization problem to generate optimal assignments.

#### 5.3. Data quality and processing

[NO INFO]

### 6. Validation schema

The system is not a predictive model, so traditional train/validation/test splits do not apply. Validation focuses on the optimization process and its output.

*   **Constraint Adherence**: The primary validation is ensuring the solver's output satisfies all defined business and logical constraints (SoV targets, placement rules, etc.).
*   **Sampling Validation**: The use of random customer sampling to manage computational scale was validated by confirming that it "leads to nearly equivalent results as optimizing all customers at once," but with a significant reduction in processing time.

### 7. Baseline solution

The primary baseline solution, which the SoV Optimization Engine is designed to outperform, is **random traffic splitting**. In this approach, customers are randomly assigned to see a message to meet the desired SoV target, without any consideration for the customer's predicted interests. For example, to achieve a 20% SoV for "Kitchen Essentials," 20% of all customers are randomly selected to see the banner.

This baseline method is also used as a fallback strategy for unrecognized customers.

### 8. Errors and their analysis

The article does not provide a formal error analysis but describes how potential undesirable outcomes are prevented via constraints in the optimization problem:

*   **Empty Placements**: Prevented by a constraint forcing each placement to be filled (`row-wise sum on the placement x message matrix to be exactly 1`).
*   **Redundant Messaging**: Prevented by a constraint that a customer does not see the same message in multiple placements (`column-wise constraint on the customer x message matrix`).
*   **Sub-optimal Placement of Important Messages**: Mitigated by incorporating a `Placement Value Matrix` into the objective function. This prevents the optimizer from satisfying SoV targets by placing high-priority messages in low-visibility placements that receive few impressions.

### 9. Training pipelines

The system uses a daily batch optimization pipeline, not a model training pipeline.

*   **Tooling**:
    *   **Solver**: Gurobi, a commercial mathematical optimization solver.
    *   **Orchestration**: The process is run as a daily batch job.
*   **Pipeline Steps**:
    1.  **Problem Definition**: The problem is formulated as a variant of the Generalized Assignment Problem. Each `[Customer, Message, Placement]` combination is a binary decision variable.
    2.  **Constraint & Objective Definition**: The SoV targets, business rules, customer-message relevance scores, and placement values are translated into mathematical constraints and an objective function for Gurobi.
    3.  **Scaling with Batching**: To handle the large scale ("billions of permutations"), the customer base is randomly sampled into smaller batches. The optimization is run in parallel on these batches.
    4.  **Solving**: The Gurobi solver is executed to find the optimal assignments for each batch.
    5.  **Output Generation**: The results are aggregated and uploaded to internal data stores and services for online consumption.

### 10. Features

The system does not use features in the traditional ML sense. The inputs are pre-computed scores and business-defined parameters.

*   **Customer-Message Relevance Score**: The most critical input. It is a numerical score representing the predicted relevance of a message to a customer. This score is sourced from upstream propensity models.
*   **Placement Value Score**: A numerical weight for each placement, reflecting its business value based on historical performance (impressions, clicks, orders).
*   **Binary Applicability/Constraint Indicators**:
    *   **Placement x Message Applicability**: A binary flag indicating if a message can be shown in a given placement.
    *   Other constraints are also translated into mathematical forms for the solver.

### 11. Measuring results

#### 11.1. Offline evaluation

The success of an optimization run is measured by the final value of the **maximized objective function** (cumulative relevance) and whether all constraints were met.

#### 11.2. A/B testing

The article mentions "successful applications," which implies that the system was validated via online A/B testing. The hypothesis for such a test would be that the SoV Optimization Engine achieves higher business metrics (e.g., clicks, conversions, revenue) compared to the baseline of random traffic splitting, while holding the Share of Voice targets constant for both groups.

#### 11.3. Reporting

The final output of the system is a simple assignment table with columns like `[CustomerID, Placement_1_MessageID, Placement_2_MessageID, ...]`. This table maps each customer to the specific message (or topic) they should see in each available placement. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_067/img_008.jpg`)

### 12. Integration and Serving

#### 12.1. API design and serving architecture

*   **Batch Pre-computation**: The system operates in a batch mode, running daily to generate the optimal `Customer x Message x Placement` assignments.
*   **Data Storage**: The output is uploaded to internal data stores/services.
*   **Online Serving**: When a recognized customer arrives on the homepage, a real-time call is made to a serving endpoint. This endpoint looks up the pre-computed assignments for that customer and returns the list of messages/topics to be displayed.
*   **Downstream Decoupling**: The SoV engine's responsibility ends at providing the "message" or "topic" (e.g., `MsgID = 2` for "Mattress"). A separate downstream application is responsible for selecting and rendering the final creative content for that topic. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_067/img_009.jpg`)

#### 12.2. SLAs and fallback strategies

*   **Fallback**: For **unrecognized customers**, the system falls back to the baseline behavior: a random assignment based on the global SoV targets. This can also serve as a general fallback if the primary system fails.
*   **Latency**: Since the assignments are pre-computed, the online serving step is a simple lookup, which should be very fast.

### 13. Monitoring

[NO INFO]

### 14. Operations

*   **Retraining Cadence**: The optimization pipeline is run **daily** to generate fresh assignments based on the latest customer data and propensity scores.
*   **Ownership**: Business teams (Marketing, Brand) are responsible for providing and updating the SoV targets. The Data Science team owns and operates the optimization engine itself.
*   **Incident Response**: [NO INFO], though the fallback mechanism for unrecognized users suggests a simple, robust alternative is available in case of failure.