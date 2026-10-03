- Company: Picnic
- Title: How we broke customer support language barriers without breaking production
- Technology area: NLP
- Source URL: https://blog.picnic.nl/how-picnic-migrated-ml-architectures-without-sacrificing-operational-continuity-271c0e04014a
- Content type: article

### 1. Problem definition

#### 1.1. Origin

Picnic's Customer Success (CS) team receives thousands of customer messages daily across various channels, including email, WhatsApp, and in-app feedback. These messages span a broad range of topics and complexity. The core problem is to classify these incoming requests to route them to the most appropriate CS agent. This ensures that complex inquiries are handled by experienced agents, while simpler questions are directed to newcomers, optimizing the agent pool's workload and effectiveness.

#### 1.2. Relevance & reasons

The existing ML system for routing, while functional for over five years, had several significant limitations that hindered scalability and performance. The business need to expand into new markets (e.g., France) and support a multilingual customer base exposed the flaws of the old architecture. Key issues included:

*   **High Maintenance Overhead:** The previous system required separate, country-specific models, leading to a proliferation of artifacts to maintain.
*   **Scalability Issues:** Rolling out to a new country like France required significant effort to replicate existing processes and train new models from scratch.
*   **Cold Start Problem:** Launching in a new market meant there was insufficient local data to train a high-performing language-specific model.
*   **Language Limitations:** The system could only confidently classify messages in the primary language of a given country (Dutch or German), failing to handle other languages like English used by expats.
*   **Performance Gaps:** The existing solution produced a "concerningly high proportion" of unclassified cases, requiring manual triage.

These challenges necessitated a migration to a more modern, unified, and multilingual ML architecture.

#### 1.3. Expectations

The new system was expected to provide a single, high-performing solution for customer message classification that could:

*   Scale easily to new countries and languages.
*   Improve classification accuracy and reduce the number of unclassified messages.
*   Unify the model architecture to reduce maintenance costs.

#### 1.4. Previous work

The incumbent system, which served as the baseline for comparison, had the following characteristics:

*   **Model:** Logistic Regression for classification.
*   **Architecture:** A set of country-and-language-specific models. It used two distinct tokenizers for Dutch and German.
*   **Scope:** Four model types were deployed for each of the two languages:
    *   Intent classification for email.
    *   Intent classification for WhatsApp.
    *   Intent classification for in-app feedback.
    *   Customer sentiment inference.
*   **Deployment:** This resulted in a total of eight different models running in production (4 types x 2 languages).
*   **Channel Differences:** The decision for channel-specific models was driven by observed differences in message characteristics:
    *   **Email:** Longer, formal style.
    *   **WhatsApp:** Shorter, more casual messages.
    *   **In-app feedback:** Very short, often just one or two sentences.

#### 1.5. Usage volumes and patterns

The system processes "thousands of questions and messages from our customers on a daily basis".

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Build a Unified System:** Replace the eight country-specific models with a single global model per use case, trainable via a generic pipeline.
*   **Improve Performance:** Significantly reduce the rate of unclassified cases and improve overall classification accuracy. The target was an improvement of at least 50% in unclassified cases.
*   **Enable Scalability:** The new architecture must trivially support new markets and languages without requiring bespoke model training for each new geography.
*   **Solve the Cold Start Problem:** Leverage data from existing markets to provide high-quality predictions for new markets (like France) from day one.
*   **Reduce Maintenance:** Drastically lower the maintenance cost and effort associated with managing multiple models.

#### 2.2. Anti-goals

*   **Avoid LLMs for this Task:** Despite their capabilities, Large Language Models (LLMs) like Llama or Mixtral were considered overkill. A hackathon confirmed that a simpler, self-hosted, and more explainable solution was preferable for this specific classification problem, especially given concerns around sensitive customer data and operational continuity.
*   **Avoid Third-Party Hosted Solutions:** The solution was to be hosted on Picnic's own cloud infrastructure to maintain control and manage costs, rather than relying on an expensive third-party equivalent.
*   **Avoid "Bleeding Edge" for its Own Sake:** The focus was on a tried, tested, and verified system that delivered value, rather than adopting the newest technology without a clear justification.

### 3. Risks and constraints

*   **Operational Criticality:** The existing issue classification model was a critical part of CS operations. Any disruption during the migration could break operational continuity.
*   **Data Sensitivity:** The system processes sensitive customer information, which influenced the decision to avoid certain technologies and favor self-hosted solutions.
*   **Legacy System Entrenchment:** The old system had been in place for over half a decade, requiring a careful migration and stakeholder management strategy to ensure a smooth transition.
*   **Aggressive Timeline:** Once the new approach was validated, business stakeholders agreed to an aggressive 8-week schedule to fully migrate all origins and markets.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **F-beta Score (β=2):** This was the key evaluation metric for the final intent classification model. The beta value of 2 was chosen to prioritize recall over precision.
    *   **Rationale:** The business cost of a message being unclassified (a false negative in terms of recall for any given class) is high, as it requires manual handling. It is more acceptable to occasionally misroute a message to the wrong agent queue (a false positive, impacting precision) than to not route it at all.
*   **Error Rate:** For the proof-of-concept model (filtering "thank you" messages), a simple error rate was used. The target was to keep this low (<4%).

#### 4.2. Online/business metrics

*   **Reduction in Unclassified Cases:** The primary business metric was the percentage decrease in messages that the model could not classify. The new model achieved a >50% reduction across all channels, and an 85% reduction for the email channel.
*   **Deflection Rate (for PoC):** The percentage of unactionable messages identified and deflected from agent queues. The PoC achieved a 50% deflection rate.
*   **FTE Savings (for PoC):** The effort saved by the PoC was translated into full-time equivalent (FTE) agents. The PoC saved the equivalent of one full-time CS agent.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   Customer support messages from three primary channels:
    *   Email
    *   WhatsApp
    *   In-app feedback
*   Data was collected from all operating countries (Netherlands, Germany, France).

#### 5.2. Labeling strategy

*   Labels (customer intents) are provided by CS agents as part of their regular workflow ("labels filled in by our customer service agents").
*   For the proof-of-concept, a specific dataset was created with messages "annotated by human experts".

#### 5.3. Dataset construction

*   **Unified Dataset:** A key architectural change was to combine messages and labels from all markets and languages into a single, unified dataset for training, testing, and evaluation.
*   **Scale:**
    *   **Proof-of-Concept:** "tens of thousands of messages".
    *   **Final Model:** "millions of rows of training data".

#### 5.4. Data quality issues

The previous system struggled to handle messages sent in a language different from the country's primary one (e.g., an expat in Germany writing in English). The unified, multilingual approach was designed to solve this.

### 6. Validation schema

#### 6.1. Train/validation/test split strategy

The article states that the unified dataset was used for "training, testing, and evaluation," which implies a standard data splitting methodology was used, but no specific details on ratios or techniques are provided.

#### 6.2. Cross-validation approach

[NO INFO]

#### 6.3. Holdout sets

[NO INFO]

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

The baseline was the pre-existing production system.

*   **Model:** Logistic Regression.
*   **Features:** Input from language-specific tokenizers (one for Dutch, one for German) and other unspecified "derived features".
*   **Architecture:** Eight separate models for two countries and four use cases (three intents, one sentiment).
*   **Weaknesses:**
    *   High maintenance cost.
    *   Poor scalability to new languages/countries.
    *   Suffered from the cold start problem.
    *   Produced a high number of unclassified cases.

### 8. Errors and their analysis

*   **Old System Errors:** The primary error was the model's inability to assign a classification with sufficient confidence, leading to a high volume of "unclassified" messages that required manual routing. It also failed on out-of-language messages.
*   **Proof-of-Concept (PoC) Analysis:** The PoC model, designed to filter out unactionable "thank you" messages, was a binary classifier. It was rolled out in one market and achieved a 50% deflection rate with an error rate of less than 4%, validating the technical approach.
*   **New System Error Trade-off:** The choice of the F2-score as the primary metric reflects a deliberate business decision to tolerate some precision errors (misclassifying a message's intent) in order to drastically improve recall (classifying as many messages as possible).

### 9. Training pipelines

#### 9.1. Tooling

*   **Model Provider:** HuggingFace.
*   **Model Architecture:** `distilbert-base-multilingual-cased`. This model was chosen to balance performance with resource needs for a multilingual use case.
*   **Infrastructure:** The entire system is self-hosted on Picnic's "own cloud infrastructure".

#### 9.2. Training process

The new training process is standardized into a "generic pipeline":

1.  **Data Aggregation:** Combine all tagged messages from all markets (Netherlands, Germany, France) into a single unified dataset.
2.  **Model Fine-tuning:** Fine-tune the `distilbert-base-multilingual-cased` model on the unified dataset for the specific classification task (e.g., intent prediction).
3.  **Artifact Generation:** The output is a single, global model artifact for that use case, deployable across all countries.

This end-to-end approach is a stark contrast to the previous method of creating country-and-language specific artifacts.

### 10. Features

*   **Feature Selection:** A significant decision was made to simplify the feature set radically. The new model uses **only the raw message text** as input.
*   **Feature Dropping:** The team "took the courageous step of dropping almost all other derived features" that were used by the previous logistic regression model. This was done to isolate and understand the predictive power of the new Transformer-based architecture.

### 11. Measuring results

#### 11.1. Offline evaluation

*   The new BERT-based model was compared against the old logistic regression baseline.
*   The new model showed a **>10% improvement in the f-beta=2 score**.

#### 11.2. A/B test design

A phased rollout strategy was used to validate and deploy the new system:

1.  **Proof of Concept (PoC):** A smaller, related problem (filtering unactionable messages) was tackled first. The model was deployed in a single market for one week. Its success (50% deflection, <4% error, 1 FTE saved) provided the confidence to proceed with the full migration.
2.  **Full System Rollout:** Following the PoC's success, an "aggressive roll-out schedule" was implemented. The team fully sunsetted the eight old models and migrated to the four new global models across all markets in **eight weeks**. This also included onboarding the new French market.

#### 11.3. Reporting

The performance improvements were described as "undeniable" and "crystal clear".

*   **Business Impact:** A massive reduction in unclassified cases:
    *   **At least 50% improvement** for all message origins.
    *   An **85% improvement** for the Email model.

### 12. Integration and Serving

#### 12.1. API design

[NO INFO]

#### 12.2. Serving architecture

*   **Model Consolidation:** The architecture was simplified from eight country-specific models to four "global models" (one per use case).
*   **Technology:** The system is described as a "full BERT end-to-end solution".
*   **Infrastructure:** All models are hosted on Picnic's own cloud infrastructure.

#### 12.3. SLAs and fallback

*   **SLA:** The system is "critical" for CS operations, implying a high availability requirement.
*   **Fallback:** The old system's fallback was manual triage for a high volume of unclassified cases. The new system drastically reduces the need for this fallback, but a mechanism for handling the remaining unclassified messages is still implicitly required.

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Retraining and maintenance

*   **Reduced Maintenance:** The new architecture, with its generic pipeline and consolidated global models, "greatly" reduces future maintenance costs.
*   **Simplified Onboarding:** Supporting new markets and languages has become a "trivial matter," as new data can be incorporated into the unified dataset for retraining without creating bespoke pipelines.

#### 14.2. Incident response and rollback

[NO INFO]