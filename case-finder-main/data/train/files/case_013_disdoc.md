- Company: Airbnb
- Title: Machine Learning-Powered Search Ranking of Airbnb Experiences
- Technology area: Predictive ML
- Source URL: https://medium.com/airbnb-engineering/machine-learning-powered-search-ranking-of-airbnb-experiences-110b4b1a0789
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The system is designed for Airbnb Experiences, a two-sided marketplace for handcrafted activities led by expert hosts. The core problem is to rank these experiences in search results to help guests find and book activities. Each experience is vetted for quality by editors before being listed.

#### 1.2. Relevance & reasons

As the marketplace grew rapidly, search, discoverability, and personalization became critical for business success. The inventory scaled from 500 experiences in 12 cities in late 2016 to over 20,000 active experiences in more than 1,000 destinations by the end of 2018. A simple or random ranking was no longer sufficient to surface relevant content from the large and diverse inventory.

#### 1.3. Expectations

The primary expectation is that an effective ranking system will help guests find the right content, leading to an increase in bookings. The system should be able to personalize results based on guest interests and trip context. For the host side of the marketplace, there is an expectation that the ranking logic is explainable, allowing hosts to understand what factors influence their position in search results.

#### 1.4. Previous work

The initial solution at launch was to "randomly re-rank Experiences daily." This approach was used to collect the initial dataset required for developing the first machine learning model.

#### 1.5. Usage volumes and patterns

The system evolved through stages corresponding to the growth of the marketplace inventory and data volume:
*   **Launch (Nov 2016):** 500 Experiences in 12 cities.
*   **Stage 1 (Small Data):**
    *   Training data: 50,000 labeled examples (clicks and bookings).
*   **Stage 2 (Mid-size Data):**
    *   Inventory: 4,000 Experiences.
    *   Training data: 250,000 labeled examples.
    *   Personalization was pre-computed for the 1 million most active users.
*   **Stage 3 (Large Data):**
    *   Inventory: 16,000 Experiences.
    *   Training data: Over 2 million labeled examples.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Primary Goal:** Increase the number of bookings on the platform.
*   **Secondary Goals (Business Rules):**
    *   **Promote Quality:** Increase the proportion of bookings for "very high quality" experiences and decrease bookings for "very low quality" ones, while keeping overall bookings neutral.
    *   **Promote New Hits:** Discover and promote promising new experiences (cold-start problem). This led to a +14% booking gain for new hits.
    *   **Enforce Diversity:** Ensure a diverse set of experience categories are shown in the top 8 results, especially for low-intent traffic. This led to a +2.3% overall booking gain.
    *   **Optimize for Low Intent:** For users searching without a specified location, optimize for click-through rate (CTR) instead of bookings. This led to a +2.2% overall booking gain.

#### 2.2. Anti-goals

*   The system should not give an excessive ranking advantage to very low-priced experiences at the expense of other quality factors. The team observed this behavior and mitigated it by removing the price feature from the model, which reduced the ranking gap without hurting overall bookings.

### 3. Risks and constraints

*   **Data Availability:** The initial model development was constrained by a small dataset. The complexity of the model had to be matched to the amount of available data.
*   **Data Leakage:** When creating personalization features, there was a risk of "leaking the label" by using information that occurred after the event used for labeling (e.g., using clicks that happened after a booking). This was mitigated by only using user interactions that occurred *before* a booking.
*   **Feature Stability:** In a fast-growing marketplace, raw count features (e.g., `number of bookings in last 7 days`) can be unstable. The system favored ratios (e.g., `bookings per 1000 viewers`) to mitigate this.
*   **Infrastructure Costs:** The Stage 2 personalization approach involved pre-computing personalized rankings for all users, which was computationally expensive (`O(NM)`, where N is users and M is experiences). This constrained the rollout to only the 1 million most active users and served as a temporary solution before building a real-time scoring infrastructure.
*   **Feature Latency:** In Stages 1 and 2, features were computed daily, leading to a latency of up to one day. This meant personalization could not react to immediate user actions.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **AUC (Area Under the Curve):** Used for offline hyper-parameter tuning and model comparison.
*   **NDCG (Normalized Discounted Cumulative Gain):** A standard ranking metric used for offline evaluation.
*   **Evaluation Method:** The offline test involved re-ranking the experiences a user clicked on within a hold-out dataset and measuring where the eventually booked experience was ranked. This was noted to have limitations and "too many assumptions."

#### 4.2. Online/business metrics

*   **Primary Metric:** Number of bookings, measured via A/B tests.
*   **Secondary Metrics:**
    *   Proportion of bookings for "very high quality" vs. "very low quality" experiences.
    *   Booking lift for new ("new hit") experiences.
    *   Click-through rate (CTR), especially for low-intent search traffic.

#### 4.3. Loss functions

*   **Stages 1-3:** Log-loss for a binary classification task.
*   **Stage 4 (Quality Objective):** Weighted log-loss. Training examples were weighted based on the quality tier of the booked experience (e.g., higher weight for bookings of "very high quality" experiences).
*   **Future Work:** The team plans to explore pairwise loss functions, which are considered more appropriate for ranking problems.

### 5. Data (Dataset)

#### 5.1. Data sources

*   Search logs: User interactions including impressions, clicks, and bookings.
*   Experience data: Attributes of the experiences themselves (price, category, duration, etc.).
*   User data: For personalization, data from logged-in users was used.
*   Airbnb Homes booking data: For guests who had booked a Home, information like trip dates, location, and party size was used to personalize Experience search.

#### 5.2. Labeling strategy

The problem was framed as a binary classification task based on user clicks:
*   **Positive Label (+1):** An experience that was clicked and subsequently booked by the user.
*   **Negative Label (-1):** An experience that was clicked but not booked.

Future work includes moving to a utility-based labeling system (e.g., impression=0, click=0.1, booking=1.0, high-quality booking=1.2).

#### 5.3. Data quality issues and cleaning

*   **Label Leakage:** To prevent leakage when generating personalization features for a given booking, only user clicks that happened *before* the booking event were used. Additionally, to avoid trivial cases, personalization features were only computed if the user had interacted with more than one experience or category.
*   **Position Bias:** Acknowledged as a known issue present in the training data, with plans to tackle it in future work.

#### 5.4. ETL

*   An offline pipeline orchestrated by **Airflow** ran daily to generate features, construct training data, and train models.
*   Future work includes improving data construction by logging feature values at scoring time instead of reconstructing them later.

### 6. Validation schema

#### 6.1. Train/validation/test split

The article mentions using "hold-out data which was not used in training" for offline hyper-parameter tuning and model comparison. The specific splitting strategy (e.g., percentage split, time-based split) is not detailed.

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets and update frequency

The system relied heavily on online A/B testing for final validation of model changes. Each major iteration (Stage 1, 2, 3, 4) was validated via an A/B test against the previous production model.
*   **Stage 1 vs. Random:** +13% booking lift.
*   **Stage 2 vs. Stage 1:** +7.9% booking lift.
*   **Stage 3 vs. Stage 2:** +5.1% booking lift.

### 7. Baseline solution

*   **Initial Baseline:** At launch, the system used a daily random re-ranking of all experiences. This was the control group for the first ML model.
*   **Iterative Baselines:** Each stage's model served as the baseline for the next iteration. For example, the Stage 1 non-personalized model was the baseline against which the Stage 2 personalized model was tested.

### 8. Errors and their analysis

*   **Diagnostic Tools:**
    *   **Partial Dependency Plots:** Used extensively to understand what the model learned and to verify that feature relationships were intuitive. For example, plots showed that higher review ratings, more bookings per viewer, and lower prices led to higher scores.
    *   **Explainability Dashboards:** Dashboards were built using **Apache Superset** and **Airflow** to track the ranking of specific experiences over time. These dashboards correlated rank changes with changes in feature values (e.g., number of reviews, price, average rating), providing a clear explanation for why a ranking improved or degraded. This was particularly useful for communicating with hosts.
*   **Error Analysis Examples:**
    *   **Rank Improvement:** An experience improved from rank 30 to 1. The dashboard showed this was due to its review count growing from 0 to 60, maintaining a 5.0 rating, and a price decrease.
    *   **Rank Degradation:** An experience dropped from rank 4 to 94. The dashboard showed this was caused by a drop in average rating (4.87 to 4.82), a price increase, and a decrease in bookings, combined with a seasonality effect for its time of day.

### 9. Training pipelines

#### 9.1. Tooling

*   **Orchestration:** **Airflow** was used to run daily offline jobs for feature generation, training, and scoring.
*   **Model:** Gradient Boosted Decision Tree (GBDT).
*   **Model Format:** The trained model was stored in a JSON format, which was then transformed into an internal Java GBDT structure for serving in production.

#### 9.2. Pipeline stages

1.  **Feature Generation:** Daily offline jobs compute Experience, User, and historical Query features.
2.  **Training Data Reconstruction:** Training data was generated by reconstructing past events from search logs.
3.  **Model Training:** GBDT models were trained. From Stage 2 onwards, two separate models were trained:
    *   A model for logged-in users with personalization features.
    *   A model for logged-out users without personalization features.
4.  **Model Deployment:**
    *   **Offline (Stages 1-2):** The output was an ordered list of experiences (or per-user lists) uploaded to production servers.
    *   **Online (Stage 3+):** The model file was loaded by the search service application on startup.

### 10. Features

#### 10.1. Feature categories

*   **Stage 1: Experience Features (25 total)**
    *   `Experience duration`, `Price`, `Price-per-hour`
    *   `Category` (e.g., cooking, music, surfing)
    *   `Reviews` (rating, number of reviews)
    *   `Number of bookings` (last 7/30 days, expressed as a ratio like bookings per 1k viewers)
    *   `Occupancy` of past and future instances
    *   `Maximum number of seats`
*   **Stage 2: User (Personalization) Features (total ~50 features)**
    *   **From Booked Home:** `Distance between Booked Home and Experience`, `Experience available during Booked Trip`, `Trip length`, `Number of guests`.
    *   **From User History:**
        *   `Category Intensity`: Weighted sum of clicks on a category in the last 15 days.
        *   `Category Recency`: Days since last click on a category.
        *   `Time of Day Fit`: Match between user's preferred time-of-day (from clicks) and the experience's time.
*   **Stage 3: Query Features (total ~90 features)**
    *   `Distance between Experience and Entered Location`
    *   Fit between `entered number of guests` and the experience's typical group size.
    *   `Experience is offered in Browser Language`
    *   `Origin-Destination Category Preference`: Category preferences for users from the searcher's country visiting that destination.

### 11. Measuring results

#### 11.1. Offline evaluation

Offline evaluation was performed on a hold-out set using AUC and NDCG metrics. The team noted that this method had "too many assumptions" and was primarily used for hyper-parameter tuning before online testing.

#### 11.2. A/B test design

All major changes were validated through online A/B tests comparing the new model to the existing production model.
*   **Hypothesis:** The new model will increase bookings or achieve a secondary business objective.
*   **Primary Metric:** Number of bookings.
*   **Key Results:**
    *   **Stage 1 (ML vs. Random):** +13% bookings.
    *   **Stage 2 (Personalization vs. Stage 1):** +7.9% bookings.
    *   **Stage 3 (Online Scoring vs. Stage 2):** +5.1% bookings.
    *   **Stage 4 (Diversity):** +2.3% bookings.
    *   **Stage 4 (Low Intent CTR):** +2.2% bookings.

#### 11.3. Reporting

Dashboards built with **Apache Superset** and **Airflow** were used to track model performance and ranking behavior. These reports were used by both the engineering team and business stakeholders (like Market Managers) to understand ranking dynamics and make decisions, such as removing the `price` feature to adjust its influence.

### 12. Integration and Serving

#### 12.1. API design

The ranking model is integrated directly into the search service. It receives query features (location, dates, guests) and user context (user ID, browser language) and returns scores for the retrieved experiences, which are then used to order the search results page.

#### 12.2. Infrastructure

The serving architecture evolved significantly:
*   **Stage 1 (Offline):** A daily job generated a single, globally-ordered list of all experiences. This list was uploaded to production machines. Ranking involved filtering this static list based on query criteria.
*   **Stage 2 (Personalized Offline):** A daily job pre-computed personalized rankings for the top 1 million active users. These rankings were stored in a look-up table keyed by `user_id`. A default ranking (key `0`) was used for all other users. This was a temporary solution.
*   **Stage 3 (Online Scoring):** A real-time scoring infrastructure was built.
    *   **Feature Stores:**
        *   **User Features:** Stored in an online key-value store for real-time lookup.
        *   **Experience Features:** Stored in-memory on the search server boxes for fast access.
        *   **Query Features:** Extracted directly from the incoming search request.
    *   **Model Serving:** The GBDT model, converted to a Java object, is loaded within the search service application. At request time, features are fetched, concatenated into a vector, and passed to the model for scoring.

#### 12.3. SLAs, latency, and fallback strategies

*   **Latency:** The move to online scoring was designed to score "thousands of listings in real time." Specific latency budgets are not mentioned.
*   **Fallback Strategy:** The online scoring system uses a fallback mechanism. If user personalization features are unavailable for a given request (e.g., a logged-out user), the system falls back from the logged-in model to the logged-out model, which does not use personalization features.

### 13. Monitoring

*   **Dashboards:** The primary monitoring tool was a set of dashboards built with **Apache Superset** and **Airflow**.
*   **Model Quality Monitoring:**
    *   **Individual Experience Tracking:** The dashboard tracked the rank of specific experiences over time and plotted it alongside key feature values (e.g., review count, rating, price). This helped explain rank changes.
    *   **Aggregate Trend Tracking:** The dashboard showed average ranking trends for different segments of experiences (e.g., by review rating, by price range, by uniqueness).
*   **Business Metric Monitoring:** The dashboards were used to ensure the ranking algorithm was enforcing desired marketplace behaviors (e.g., rewarding high-quality experiences).
*   **Drift Detection:** The dashboards implicitly monitored for drift and seasonality by tracking feature popularity. For example, one analysis noted that the "early morning" time slot became less popular in a market, affecting the rank of experiences held at that time.

### 14. Operations

#### 14.1. Retraining cadence

The entire pipeline, including feature generation and model training, was run daily, orchestrated by **Airflow**. Feature updates for the online serving system also occurred on a daily basis.

#### 14.2. Incident response and rollback procedures

[NO INFO]

#### 14.3. Non-engineering considerations

*   **Host Feedback:** A major operational consideration was providing explainability for hosts. The monitoring dashboards were used by Airbnb's Market Managers to give hosts "concrete feedback on what factors lead to improvement in the ranking and what factors lead to decline."
*   **Business Rule Integration:** The system was adapted to handle multiple business objectives beyond just maximizing bookings, such as promoting quality and diversity. This required collaboration with business teams (e.g., the Quality Team) to define objectives and translate them into ML solutions like weighted loss functions.
*   **Future Human-in-the-Loop:** The team is exploring a "human-in-the-loop" approach, such as incorporating "Staff picks," as part of future work.