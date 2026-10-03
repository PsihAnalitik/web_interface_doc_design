- Company: Mercado Libre
- Title: How we design our push notifications strategy so that customers interact with our product
- Technology area: Predictive ML
- Source URL: https://medium.com/mercadolibre-tech/how-we-design-our-push-notifications-strategy-so-that-customers-interact-with-our-product-fda8a3c4be01
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The system is designed to improve the effectiveness of push notifications for Mercado Libre's "Marketplace In Store" project. This project encompasses the catalog of physical stores that use Mercado Pago QR as a payment method. Users are constantly receiving notifications from many apps, leading them to overlook important ones. The goal is to generate attractive push notifications by detecting opportunities within user behavior, communicating effectively without being perceived as spam.

#### 1.2. Relevance & reasons

A good product needs to be promoted to drive recurring and habitual use. The previous method of sending notifications was based on ad-hoc, uncoordinated strategies. This created a risk of channel saturation, where multiple, unrelated notifications could be sent to the same user, leading to audience exhaustion and a poor user experience.

A coordinated system creates a "virtuous circle":
1.  Effective notifications boost user awareness and usage of QR payments.
2.  Increased usage makes the platform more attractive to sellers.
3.  More sellers lead to better offers, which in turn enhances the product for users.

#### 1.3. Expectations

The system is expected to orchestrate all notification strategies, selecting the best possible notification for each user from all available options. The process must be scalable and dynamic, allowing for the easy addition of new strategies to adapt to changing business needs and market initiatives.

#### 1.4. Previous work

Prior to this system, communications with users were "ad-hoc and not related to one another." Automated mailings were sent without interpreting the relationship across different strategies, which could lead to channel saturation. One such ad-hoc strategy, referred to as "Favorite," was used as a baseline for comparison.

#### 1.5. Usage volumes and patterns

[NO INFO]

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Increase User Interaction**: Boost the open rate of push notifications and subsequent interaction with the Mercado Pago QR product.
*   **Personalization**: Select the best notification strategy for each user and the best specific offer (e.g., store) within that strategy.
*   **Avoid Channel Saturation**: Implement a "conciliator" to deduplicate notifications across all strategies, ensuring a user receives only the single most relevant message.
*   **Scalability**: Create a modular and abstract structure that allows for the easy addition of new notification strategies without re-architecting the system.
*   **Effectiveness**: Communicate effectively with a smaller, more targeted universe of users to provide value and service.

#### 2.2. Anti-goals

*   **Avoid Being a Nuisance**: The system should not send communications that are perceived as spam or lead to "audience exhaustion."
*   **Avoid Over-Communication**: The system should not overestimate the number of mailings required.
*   **Avoid Atomized Communications**: The system should not send multiple uncoordinated notifications from different strategies to the same user.

### 3. Risks and constraints

#### 3.1. Risks

*   **Operational Errors**: An error in the dynamic content allocation step is considered critical, as it "could potentially unleash thousands of notifications" with incorrect content.
*   **Channel Saturation**: If the cross-strategy deduplication ("conciliation") fails, the system could revert to sending multiple, uncoordinated notifications, annoying users.
*   **Audience Exhaustion**: If the selected strategies are not relevant, users may become desensitized to notifications, defeating the system's purpose.

#### 3.2. Constraints

*   **Data Sparsity**: User geolocation data is only available when users explicitly agree to share it. This makes determining a user's "frequent location" an estimation rather than a precise measurement, which impacts location-based strategies.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Affinity Score (for Market Basket strategy)**: A custom metric was developed to measure the affinity between two Merchant Category Codes (MCCs). Instead of traditional conditional probability, it compares the sequence probability against the probability of a second payment occurring in the entire universe. The formula is:
    `Affinity(MCC2 | MCC1) = P(MCC2 | MCC1) / P(MCC2 | Any second payment)`
    Affinities greater than 1 were considered significant.
*   **Potential Reach**: For the "From ON to OFF" strategy, an analysis was conducted to estimate the percentage of interested users who could be reached with an offer within a certain distance. For example, an offer within 2 km could reach 41.33% of interested users.

#### 4.2. Online/business metrics

*   **Open Rate**: This is the primary effectiveness metric used for comparing strategies. It is defined as:
    `Open Rate = (Number of notifications opened) / (Number of notifications shown)`

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **User Payment History**: Transaction data from Mercado Pago, including the Merchant Category Code (MCC) of purchases and timestamps. Used for the "Market Basket" strategy.
*   **User Marketplace Behavior**: Data on user interests from the Mercado Libre marketplace, such as products viewed and categories searched. Used for the "From ON to OFF" strategy.
*   **User Geolocation**: GPS coordinates shared by users via the mobile app. This data is sparse.
*   **Store Catalog**: Information about physical stores that accept QR payments, including their location and MCC.

#### 5.2. Labeling strategy

The system does not use explicitly labeled data for training in a traditional sense. Instead, it relies on user behavior as signals of interest. The online "open rate" serves as a proxy label for the relevance and success of a notification.

#### 5.3. Data quality issues

The primary issue mentioned is the sparsity of geolocation data, as it depends on user consent. This required estimating a user's "frequent location" rather than knowing it precisely.

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

[NO INFO]

### 7. Baseline solution

The baseline was the previous system of ad-hoc, uncoordinated communication strategies. A specific strategy from this system, named **"Favorite"**, was used as a benchmark in production. The "Favorite" strategy aimed to contact users by offering stores from categories they were presumed to like, but it was not orchestrated with other campaigns. The new system's performance was measured against this baseline.

### 8. Errors and their analysis

[NO INFO]

### 9. Training pipelines

The system is described as a multi-stage orchestration process rather than a traditional model training pipeline. The development was carried out on Mercado Libre's internal ML platform, **Fury Data Apps**, using **Python**.

The pipeline consists of the following modular components:

1.  **Target Definition**: Define the set of items to be notified (e.g., stores in a specific category, stores with a certain benefit).
2.  **Audience Generation**: For each item in the `Target`, identify potential user prospects based on criteria like proximity or interests. This creates a set of (user, target) pairs with an N-to-N cardinality.
3.  **Filtering**: Remove pairs from the audience based on business logic, such as not notifying users who recently received a similar notification.
4.  **Scoring (Intra-strategy)**: For each strategy, score the filtered (user, target) pairs. This step can use a simple heuristic or a machine learning model score. The goal is to deduplicate the N-to-N relationship and select the single best store for each user within that strategy's context.
5.  **Conciliation (Inter-strategy)**: This is a global deduplication step. It takes the winning candidate notifications from all parallel strategies and selects the single best one for each user. This step also uses a scoring mechanism (heuristic or model-based) to prioritize across strategies.
6.  **Notification Triggering**: The final selected communication is sent as a push notification. This step considers the optimal contact time for the specific store and dynamically allocates the message content based on the winning strategy.

### 10. Features

#### 10.1. Feature categories

*   **Transactional Features**:
    *   Sequence of purchases by Merchant Category Code (MCC).
    *   Time elapsed between purchases (e.g., within a two-hour lapse for the Market Basket strategy).
*   **User Interest Features**:
    *   Product categories searched or viewed on the Mercado Libre marketplace.
    *   Implicit purchase intent (e.g., showing interest in a product but not completing the purchase).
*   **Geospatial Features**:
    *   User's estimated "frequent location".
    *   Distance between a user's location and a physical store.
*   **Store Features**:
    *   Store's MCC.
    *   Discounts or benefits offered by the store.

#### 10.2. Feature selection

For the "From ON to OFF" strategy, item categories were selected based on whether they had a clear correlation between the online marketplace and physical stores.

### 11. Measuring results

#### 11.1. Offline evaluation

An analysis was performed for the "From ON to OFF" strategy to estimate potential user reach. It was found that offering a store within a 2 km radius could reach 41.33% of users who had shown interest in a corresponding online category. The search radius used in practice varies by category.

#### 11.2. A/B test design

The new strategies were compared against the baseline "Favorite" strategy in a live production environment.
*   **Hypothesis**: The new, orchestrated strategies will have a higher open rate than the old, ad-hoc strategies.
*   **Metric**: Open Rate.
*   **Results**: The new initiatives yielded better results. A strategy named "Similar to Favorites," built on the new framework, was directly compared to the old "Favorite" strategy. The new strategy's performance was "undoubtedly better," in some cases **doubling the open rate percentage** of the ad-hoc initiative. Results were tracked via daily and accumulated data graphs.

### 12. Integration and Serving

#### 12.1. API design

The final output of the system is a push notification sent to a user's mobile phone. The process appears to be a batch job that generates and conciliates notification candidates before triggering the send.

#### 12.2. Infrastructure

The entire process runs on **Fury Data Apps**, Mercado Libre's internal Machine Learning platform.

#### 12.3. SLAs, latency budgets, and fallback strategies

*   **SLAs**: The system considers the "optimum time of contact for each store" before sending the notification, but no specific latency budgets for the generation pipeline are mentioned.
*   **Fallback Strategies**: [NO INFO]

### 13. Monitoring

#### 13.1. Data quality and schema checks

[NO INFO]

#### 13.2. Model quality and prediction drift

The primary metric for monitoring the effectiveness of the strategies is the **open rate**. This is tracked on a daily and accumulated basis to compare performance across different initiatives.

#### 13.3. Input/target drift detection

[NO INFO]

#### 13.4. Engineering metrics

[NO INFO]

### 14. Operations

#### 14.1. Retraining cadence and ownership

The system is designed to be flexible, allowing new strategies to be added or prioritized easily according to business needs (e.g., targeted discounts). The article does not specify a fixed retraining or model update cadence. The system was developed by the "Marketplace In Store" project team.

#### 14.2. Incident response and rollback procedures

The article highlights that the dynamic content allocation step is "a critical part of the process as any error could potentially unleash thousands of notifications," which implies that checks are in place, but no specific incident response or rollback procedures are described.