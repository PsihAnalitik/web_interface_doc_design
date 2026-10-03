**Company:** Microsoft
**Title:** Large-language models for automatic cloud incident management
**Technology area:** Generative AI & LLM
**Source URL:** https://www.microsoft.com/en-us/research/blog/large-language-models-for-automatic-cloud-incident-management/
**Content type:** article

### 1. Problem definition

#### 1.1. Origin

The system is designed to address the challenges of managing production incidents for hyperscale cloud services like Microsoft 365 (M365). The primary users are on-call engineers responsible for incident resolution. The core problem is to accelerate the process of performing root cause analysis and defining mitigation steps, which is currently a challenging and manual process.

#### 1.2. Relevance & reasons

M365 supports hundreds of thousands of organizations, making service reliability critical. Quickly resolving production incidents is essential to minimize customer impact. Previous internal research on Microsoft Teams incidents revealed the lifecycle and common patterns of incidents, leading to the vision that AIOps could automate and improve incident diagnosis. The goal is to leverage state-of-the-art Large Language Models (LLMs) to automate the generation of root cause and mitigation recommendations, thereby reducing human effort and improving service resilience by learning from past incidents.

#### 1.3. Expectations

The system is expected to take an incident's title and summary as input and generate relevant recommendations for both the root cause and the necessary mitigation steps. The recommendations should be useful enough to accelerate the incident resolution process for on-call engineers. A future expectation is to evolve this into a conversational interface that can be actively integrated into the incident diagnosis discussion.

#### 1.4. Previous work

A prior study, "How to Fight Production Incidents? An Empirical Study on a Large-scale Cloud Service," provided a comprehensive, multi-dimensional empirical study of production incidents from Microsoft Teams. This foundational work analyzed the incident lifecycle, common root causes, and mitigation strategies, which informed the current project's direction toward using AI for automated diagnosis.

#### 1.5. Usage volumes and patterns

The research and evaluation were conducted on a dataset of more than 40,000 production incidents generated from over 1,000 distinct services within Microsoft.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Automate Diagnosis:** Automatically generate recommendations for the root cause and mitigation steps for a given cloud incident.
*   **Accelerate Resolution:** Reduce the time required to resolve an incident, thereby minimizing customer impact.
*   **Reduce Human Effort:** Decrease the manual effort required from on-call engineers during incident management.
*   **Improve Service Resilience:** Leverage lessons from past incidents to build a more resilient system for the future.
*   **Enhance Customer Satisfaction:** Improve overall service reliability and customer satisfaction by resolving issues faster.

#### 2.2. Anti-goals

[NO INFO]

### 3. Risks and constraints

*   **Model Staleness:** The effectiveness of the models may degrade over time as new types of incidents occur. The models need to be frequently retrained with the latest incident data to remain relevant.
*   **Limited Context:** The initial version of the system relies only on the incident title and summary. It lacks access to richer contextual information such as discussion logs, service metrics, and dependency graphs, which could limit the accuracy and usefulness of its recommendations.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The system's performance was evaluated using a combination of lexical and semantic similarity metrics, comparing the generated text to the ground truth from historical incidents. Metrics were calculated for both Top-1 and Top-5 generated recommendations.

*   **Lexical Similarity Metrics:**
    *   BLEU-4
    *   ROUGE-L
    *   METEOR
*   **Semantic Similarity Metrics:**
    *   BERTScore
    *   BLEURT
    *   NUBIA

#### 4.2. Online/business metrics

*   **Human Evaluation:** The usefulness of the generated recommendations was evaluated through interviews with incident owners in a real-time production setting.
    *   **Metric:** A qualitative rating on a scale of 1 to 5.
    *   **Result:** Over 70% of on-call engineers provided a usefulness rating of 3 out of 5 or better.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The primary data source is the internal Incident Management (IcM) portal at Microsoft. The dataset consists of over 40,000 historical production incidents from more than 1,000 services.

#### 5.2. Labeling strategy

The system uses historical incident data as its ground truth. For each incident, the root cause and mitigation steps documented by engineers in the IcM portal upon resolution are used as the target labels for training and evaluation.

#### 5.3. Available metadata

Each incident record contains:
*   Incident Title
*   Incident Summary (describing error messages, anomalous behavior, etc.)
*   Ground Truth Root Cause
*   Ground Truth Mitigation Steps
*   Incident Type: The data distinguishes between Machine Reported Incidents (MRIs) and Customer Reported Incidents (CRIs).

#### 5.4. Data quality issues

The performance difference between incident types suggests variability in data structure. LLMs performed better on MRIs, which was attributed to their repetitive and more structured nature compared to CRIs.

### 6. Validation schema

[NO INFO]

### 7. Baseline solution

The study did not use a simple heuristic baseline. Instead, it compared the performance of several state-of-the-art language models in different settings (zero-shot, fine-tuned, multi-task). The models evaluated include:

*   RoBERTa
*   CodeBERT
*   GPT-3 models (Curie, Codex, Davinci)
*   GPT-3.5 model (Davinci-002)

The GPT-3.5 model (Davinci-002) was identified as the best-performing model among those tested.

### 8. Errors and their analysis

*   **Model Performance Variance:** GPT-3.5 (Davinci-002) significantly outperformed GPT-3 models. For root cause and mitigation recommendation tasks, Davinci-002 achieved at least 15.38% and 11.9% gains, respectively, over all GPT-3 models.
*   **Impact of Fine-Tuning:** Fine-tuning the models on incident-specific data yielded substantial improvements over the zero-shot approach. A fine-tuned GPT-3.5 model improved the average lexical similarity score by 45.5% for root cause generation and 131.3% for mitigation generation.
*   **Data Type Sensitivity:** Models performed better on Machine Reported Incidents (MRIs) compared to Customer Reported Incidents (CRIs), likely due to the more structured and repetitive nature of MRI descriptions.
*   **Future Mitigation Strategies:** To address current limitations (staleness and lack of context), future work will focus on:
    *   Incorporating additional data sources like discussion entries, logs, service metrics, and service dependency graphs.
    *   Implementing retrieval-augmented generation (RAG) approaches to provide the model with relevant, up-to-date context from historical incidents, troubleshooting guides, and an internal engineering knowledge base. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_001/img_004.jpg`)

### 9. Training pipelines

#### 9.1. Tooling

The research utilized GPT-3 and GPT-3.5 models, implying the use of Microsoft's internal or Azure-based AI infrastructure for fine-tuning and inference.

#### 9.2. Pipeline stages

The model development process involved evaluating models in several settings:
1.  **Input:** The model takes the incident title and summary as text input. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_001/img_003.jpg`)
2.  **Zero-shot Inference:** Generating recommendations directly using the pre-trained base LLMs without any further training.
3.  **Fine-tuning:** Adapting the pre-trained LLMs by further training them on the dataset of 40,000+ historical incidents.
4.  **Multi-task Learning:** [inferred] A setting where the model might be trained on multiple related tasks simultaneously, such as generating the root cause and mitigation steps together. The article mentions this setting but provides no further details.
5.  **Output:** The model generates text for the predicted root cause and mitigation steps.

#### 9.3. Experiment tracking and CI/CD

[NO INFO]

### 10. Features

#### 10.1. Feature categories

The primary features are raw text from the incident tickets.
*   **Incident Title:** The title assigned to the incident ticket.
*   **Incident Summary:** A natural language description of the incident, including error messages and observed anomalous behavior.

#### 10.2. Future features

Future iterations plan to incorporate a wider range of contextual information:
*   Incident discussion entries
*   Logs
*   Service metrics
*   Dependency graphs of impacted services

### 11. Measuring results

#### 11.1. Offline evaluation

A rigorous offline evaluation was conducted by comparing model-generated text against the ground truth from the IcM portal using a suite of metrics.

*   **Comparison:** The performance of GPT-3.5 was compared against three GPT-3 models (Curie, Codex, Davinci) and other baselines like RoBERTa and CodeBERT.
*   **Key Result:** The fine-tuned GPT-3.5 model demonstrated significant improvements, such as a 131.3% increase in the average lexical similarity score for mitigation generation tasks compared to its zero-shot performance.

| Model | BLEU-4 (Top1) | ROUGE-L (Top1) | METEOR (Top1) | BERTScore (Top1) | BLEURT (Top1) | NUBIA (Top1) |
|---|---|---|---|---|---|---|
| RoBERTa | 4.21 | 12.83 | 9.89 | 85.38 | 35.66 | 33.94 |
| CodeBERT | 3.38 | 10.17 | 6.58 | 84.88 | 33.19 | 39.05 |
| Curie | 3.40 | 19.04 | 7.21 | 84.90 | 32.62 | 33.52 |
| Codex | 3.44 | 8.98 | 7.33 | 84.85 | 32.50 | 33.64 |
| Davinci | 3.34 | 8.53 | 6.67 | 83.13 | 31.06 | 35.28 |
| Davinci-002 | 4.24 | 11.43 | 10.42 | 85.42 | 36.77 | 32.3 |

#### 11.2. A/B test design

A formal A/B test was not described. Instead, a qualitative human evaluation was conducted.

*   **Hypothesis:** Recommendations generated by the LLM are useful for on-call engineers during incident resolution.
*   **Methodology:** Interviewed incident owners and asked them to rate the usefulness of the generated recommendations for real incidents.
*   **Success Criteria:** A usefulness rating of 3 out of 5 or better was considered a positive signal.
*   **Result:** More than 70% of engineers gave a rating of 3/5 or higher, validating the model's practical utility.

### 12. Integration and Serving

#### 12.1. API design

The system is designed to function as a recommendation engine.
*   **Input:** Incident Title and Summary (text).
*   **Output:** Recommended Root Cause and Mitigation Steps (text).
(see image: `ml-design-doc-reviewer/data/raw_documents/images/case_001/img_003.jpg`)

#### 12.2. Future integration

The long-term vision is to move beyond a simple recommendation API to a more interactive system.
*   **Conversational Interface:** Integrate the model into the incident "discussion" to provide contextual suggestions and facilitate the resolution process.
*   **Retrieval-Augmented Generation (RAG):** The conversational agent would use a retriever to pull information from a corpus of historical incidents, troubleshooting guides, and an engineering hub to provide more accurate and context-aware responses. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_001/img_004.jpg`)

#### 12.3. Infrastructure

[NO INFO]

#### 12.4. SLAs and fallback strategies

[NO INFO]

### 13. Monitoring

The article highlights the problem of model "staleness," which implies a need for ongoing monitoring of model performance, but does not detail a specific monitoring strategy. Future work on retrieval-augmented approaches is partly a solution to keep the model's knowledge current without constant retraining.

*   **Data Quality Monitoring:** [NO INFO]
*   **Model Quality Monitoring:** [NO INFO]
*   **Engineering Metrics:** [NO INFO]
*   **Alerting:** [NO INFO]

### 14. Operations

#### 14.1. Retraining cadence

The need to keep models from becoming stale is emphasized, requiring them to be "frequently retrained with the latest incident data." However, a specific cadence (e.g., daily, weekly) is not provided.

#### 14.2. Incident response and rollback

[NO INFO]