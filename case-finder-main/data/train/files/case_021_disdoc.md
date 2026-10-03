**Company**: Roblox
**Title**: How Roblox Uses AI to Moderate Content on a Massive Scale
**Technology Area**: Generative AI & LLM
**Source URL**: https://corp.roblox.com/newsroom/2025/07/roblox-ai-moderation-massive-scale
**Content Type**: article

### 1. Problem definition

#### 1.1. Origin

The problem is to proactively moderate user-generated content (UGC) on the Roblox platform at a massive scale to maintain a safe and civil environment for users. The system must handle various content modalities, including text chat, voice communication, images, and other user-created assets, across multiple languages.

#### 1.2. Relevance & reasons

With a large and active user base, manual moderation is infeasible. The platform's scale necessitates automated, AI-driven systems. Historically, moderation was done by human reviewers, including the company's founder. As the platform grew, this became unsustainable. The volume of content produced daily demands scalable infrastructure, machine learning (ML) models, and purpose-built tools to ensure safety, which is a foundational principle for the company.

#### 1.3. Expectations

The system is expected to operate in near real-time to provide immediate feedback to users and prevent exposure to inappropriate content.
*   **Text Filtering**: Must react in milliseconds.
*   **Voice Moderation**: Must assess violations within 15 seconds.
*   **Illegal Content**: The median time to action upon receiving a notice of illegal content is ten minutes.

#### 1.4. Previous work

*   **Human Moderation**: In the early days of Roblox, content was moderated manually by human reviewers.
*   **Rules-Based Filter**: Over a decade ago, a rules-based text filter was built as the first automated solution.
*   **Transformer-Based Filter**: Approximately five years ago, a state-of-the-art transformer-based text filter was deployed.

#### 1.5. Usage volumes and patterns

*   **Users**: 97.8 million daily active users (as of Q1 2025).
*   **Content Volume**:
    *   Approximately 1 trillion pieces of content were uploaded between February and December 2024.
    *   An average of 6.1 billion chat messages are sent per day.
    *   An average of 1.1 million hours of voice communication occurs per day.
    *   Millions of assets are uploaded by creators daily.
*   **Violation Rate**: As little as 0.01% of content was detected as violating policies. Almost all of this was prescreened and removed automatically.
*   **Languages**: The platform supports communication in 28 different languages.
*   **System Load**:
    *   The text filter system processes over 750,000 requests per second (RPS) in total.
    *   The PII (Personally Identifiable Information) filter model handles 370,000 RPS at peak.
    *   The voice safety classifier handles up to 8,300 RPS at peak.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Proactive Moderation**: Automatically moderate content before users are exposed to it.
*   **Real-Time Feedback**: Provide immediate feedback to users (e.g., warnings, notifications) to educate them and change behavior.
*   **High Performance**: Deploy AI only when it performs significantly higher in both precision and recall than humans at scale.
*   **Continuous Improvement**: Innovate along three dimensions: scale, speed, and quality, using high-quality data and active learning.
*   **Human-in-the-Loop**: Leverage thousands of human experts for continuous AI improvement, handling evolving and rare cases, complex investigations, and appeals.

#### 2.2. Anti-goals

*   **Sole Reliance on AI**: The system should not completely replace human judgment. Humans are explicitly kept in the loop for nuanced cases, appeals, and system training.
*   **Over-optimization for Precision**: While minimizing false positives is important to avoid user frustration, the system is designed to err on the side of removing potentially violating content (i.e., prioritizing recall/fewer false negatives).

### 3. Risks and constraints

*   **Evolving Evasion Tactics**: Users constantly introduce new slang, memes, and methods to evade moderation, requiring the system to adapt continuously.
*   **Adversarial Attacks**: The system is tested by AI-assisted red teams (AARTs) who simulate adversarial attacks to probe for weaknesses.
*   **Infrastructure Scale**: The high volume of requests per second (RPS) puts a strain on the serving stack, necessitating significant infrastructure investments (e.g., moving from CPU to GPU) and model optimizations (quantization, distillation).
*   **Real-Time Latency**: The system is constrained by strict latency budgets: milliseconds for text filtering and under 15 seconds for voice moderation.
*   **Multilingual and Multimodal Complexity**: The system must effectively moderate content across 28 languages and multiple modalities (text, voice, images, 3D assets).

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Precision and Recall**: The primary metrics for model performance. The goal is for AI to be "significantly higher" on both compared to humans at scale.
*   **False Positive Rate (FPR)**: The voice safety classifier has a 1% FPR. An improved PII filter reduced false positives by 30%.
*   **Recall Rate**: The latest version of the voice classifier has a 92% higher recall than the initial version.
*   **Labeler Alignment**: An inter-annotator agreement metric. If alignment between human labelers is below 80%, the policy or training materials are considered confusing and are iterated upon.
*   **Labeler Quality**: Assessed by having human experts label a "golden set" of examples to ensure policies can be enforced correctly and consistently.

#### 4.2. Online/business metrics

*   **PII Mentions Detected**: The improved PII filter led to a 25% increase in automatically detected PII mentions.
*   **Reduction in Filtered Chat**: In-experience text chat notifications resulted in a 5% reduction in filtered chat messages.
*   **Reduction in Abuse Reports**: The same notifications led to a 6% reduction in consequences from abuse reports.
*   **Reoffense Rate**: Suspensions were shown to reduce reoffense rates for up to three weeks.
*   **Median Time to Action**: The median time to act on reports of illegal content is 10 minutes.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Live Platform Data**: Billions of daily chat messages, voice communications, and asset uploads.
*   **User Abuse Reports**: A primary source of labeled data. A reporting tool allows users to capture an entire scene, including avatar/object IDs, and visually highlight the issue. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_021/img_003.webp`)
*   **User Appeals**: When a moderation decision is overturned on appeal, the example is added to the training dataset.
*   **Expert Curation**: Policy experts hand-curate a "golden set" of high-quality examples that closely match target issues.
*   **Adversarial Probing**: AI-assisted red teams (AARTs) generate data by simulating attacks to find system weaknesses.
*   **Synthetic Data**: Large language models (LLMs) are used to generate millions of artificial data examples and labels, especially for rare or edge cases.

#### 5.2. Labeling strategy

A hybrid approach combining human and AI labeling is used. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_021/img_001.webp`)
*   **Human Labeling**: Thousands of human experts and skilled labelers around the world review and label data.
*   **AI-Assisted Labeling**: [inferred] AI models assist in the labeling process.
*   **LLM-based Labeling**: LLMs generate synthetic data along with corresponding labels.

#### 5.3. Data quality issues and cleaning

*   **Data Freshness**: The system must handle transient data like new slang and memes.
*   **Data Curation**: Various sampling strategies are used to build effective training datasets:
    *   **Uncertainty Sampling**: Sampling edge cases where the model was previously confused.
    *   **Large-scale Sampling**: Sampling from very large datasets.
*   **Label Quality Control**: A rigorous process is in place to ensure data accuracy:
    *   **Alignment Check**: Inter-annotator agreement is measured and must be >= 80%.
    *   **Quality Check**: Labeler accuracy is tested against the "golden set." If quality or alignment is low, the policy definition and training are re-evaluated.

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

#### 6.1. Train/validation/test split

Labeled data is split into a training dataset and an evaluation dataset. The importance of a robust evaluation set that is not "too easy" is emphasized to prevent models from appearing to work well but failing in production.

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets

A "golden set" of examples hand-curated by policy experts serves as a high-quality holdout set for evaluating model quality and ensuring policies can be enforced correctly.

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

*   **Rules-Based System**: A historical baseline was the rules-based text filter built over a decade ago.
*   **Previous Model Versions**: New models are benchmarked against their predecessors. For example, the latest voice classifier's 92% higher recall is relative to the "initial version."
*   **Human Performance**: AI models are only deployed if they achieve significantly higher precision and recall than human moderators at scale.

### 8. Errors and their analysis

#### 8.1. Error taxonomy

*   **False Negatives (Missed Violations)**: The system is intentionally biased to minimize these, "erring on the side of removing anything that could include a policy violation."
*   **False Positives (Incorrect Takedowns)**: Acknowledged as a source of user frustration. Efforts are made to minimize them, such as the 30% reduction in FPs for the PII filter.

#### 8.2. Residual analysis

*   **Appeals Process**: Incorrect decisions overturned on appeal are fed back into the training data as corrective examples.
*   **Uncertainty Sampling**: The system actively trains on examples where the model was previously "confused" to improve its handling of edge cases.
*   **Red Teaming**: AI-assisted red teams proactively search for weaknesses and failure modes, generating adversarial examples for training.

### 9. Training pipelines

#### 9.1. Tooling

*   **Models**: The system is underpinned by large, transformer-based multimodal models.
*   **Optimization**: Models are optimized for production using distillation and quantization to maintain speed and efficiency.
*   **Infrastructure**: Training and inference run on a custom infrastructure that includes GPUs and a "cellular infrastructure." (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_021/img_001.webp`)

#### 9.2. Automation

*   **Active Learning**: The system employs "active learning systems" that "continuously update models as language evolves, user patterns change, and real-world events happen." This suggests a continuous training and deployment cycle.
*   **AI-driven Rules**: The team is exploring automatically creating AI-driven rules from user reports to increase responsiveness between full model training cycles.

#### 9.3. Experiment tracking

[NO INFO]

### 10. Features

#### 10.1. Feature categories

The system is multimodal and uses features from:
*   **Text**: Raw text from chat messages.
*   **Audio**: Voice communications.
*   **Visual**: Images and other uploaded assets.
*   **Contextual Metadata**: User reports can include scene information, avatar IDs, and object IDs, providing additional context.

#### 10.2. Feature store

[NO INFO]

#### 10.3. Feature importance

[NO INFO]

### 11. Measuring results

#### 11.1. Offline evaluation

Models are assessed against a robust evaluation dataset using metrics like precision, recall, and label alignment before deployment.

#### 11.2. A/B testing

"Experiments" are conducted in production to measure the impact of new features.
*   **Hypothesis**: An experiment with real-time text chat notifications hypothesized that such interventions would improve user behavior.
*   **Results**: The experiment confirmed the hypothesis, showing a 5% reduction in filtered chat messages and a 6% reduction in consequences from abuse reports.

#### 11.3. Reporting

Internal research and analysis are used to measure the broader impact of moderation actions, such as the finding that suspensions reduce reoffense rates for up to three weeks.

### 12. Integration and Serving

#### 12.1. API design

The system operates as a high-throughput service, handling "requests per second" (RPS) for content analysis.

#### 12.2. Infrastructure

*   **Serving Stack**: A custom-built serving stack on GPUs was developed to handle high RPS demands, replacing a previous CPU-based stack.
*   **Architecture**: The system leverages a "cellular infrastructure."
*   **Performance Optimizations**:
    *   Separation of tokenization from inference.
    *   Quantization and distillation of large models.
    *   These improvements quadrupled the RPS for the PII filter.

#### 12.3. SLAs, latency budgets, and fallback strategies

*   **SLAs**:
    *   Text filtering: Milliseconds.
    *   Voice moderation: Within 15 seconds.
*   **Fallback Strategies**:
    *   **Human Review**: Thousands of human experts handle complex cases, appeals, and investigations that are beyond the AI's capabilities.
    *   **Layered Defenses**: The system uses a multi-layered approach, starting with warnings and escalating to time-outs and suspensions. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_021/img_002.webp`)
    *   **Rapid Rules**: Exploring the automatic creation of AI-driven rules from user reports for faster response times than full model retraining.

#### 12.4. Release cycle

[NO INFO]

### 13. Monitoring

*   **Data and Model Drift**: "Active learning systems" are in place to continuously update models in response to evolving language, changing user patterns, and real-world events, implying constant monitoring for drift.
*   **Business Metrics**: Key behavioral metrics like reoffense rates and the volume of filtered messages are tracked to assess the system's effectiveness.
*   **Engineering Metrics**: System load is monitored via Requests Per Second (RPS), with specific figures cited for peak loads on different models (e.g., 370k RPS for PII filter).
*   **Alerting**: [NO INFO], but the 10-minute median action time for illegal content suggests a robust alerting and on-call system for high-severity reports.

### 14. Operations

#### 14.1. Retraining cadence

The system uses a continuous update model ("active learning") rather than a fixed retraining schedule, allowing it to adapt rapidly to new trends.

#### 14.2. Ownership

A hybrid team of AI systems and "thousands of human experts" operates the system. The human experts provide oversight, continuous training, handle appeals, and manage complex investigations. Policy experts are responsible for curating "golden sets" of data.

#### 14.3. Incident response

*   **User-driven Feedback**: The user appeals process and abuse reporting system are core components for identifying and correcting system errors (false positives and false negatives).
*   **Rollback Procedures**: [NO INFO]

#### 14.4. Non-engineering considerations

*   **User Education**: The system is designed to educate users through real-time feedback, such as on-screen notifications and warnings.
*   **Escalating Consequences**: A clear policy of escalating consequences is enforced, from warnings to time-outs and suspensions, to manage repeat offenders.
*   **Community Involvement**: The abuse reporting tool empowers tens of millions of users to act as an extension of the moderation team.