**Company**: Linkedin
**Title**: JUDE: LLM-based representation learning for LinkedIn job recommendations
**Technology area**: Generative AI & LLM
**Source URL**: https://www.linkedin.com/blog/engineering/ai/jude-llm-based-representation-learning-for-linkedin-job-recommendations
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The project, named Job Understanding Data Expert (JUDE), aims to improve LinkedIn's job recommendation system by leveraging Large Language Models (LLMs) to generate high-quality vector embeddings. The system is designed to understand and represent textual data from three core entities: Jobs (descriptions), Member profiles, and Member resumes. These embeddings are fundamental features that power the entire job recommendation stack, which connects qualified candidates with relevant job opportunities on the LinkedIn platform.

#### 1.2. Relevance & reasons

LLM-based embeddings offer several advantages over previous methods:
*   **Compression**: They convert large-scale, sparse, high-dimensional data into manageable, dense vectors, reducing computational complexity.
*   **Performance**: They capture intricate semantic relationships and patterns in text data, improving recommendation accuracy beyond simple keyword matching.
*   **Transfer Learning**: The learned representations can be shared across different downstream tasks and models.
*   **Interoperability**: They facilitate integration between different ML frameworks (e.g., PyTorch vs. TensorFlow).

The JUDE platform was developed to address the significant technical challenges of deploying LLMs in a production environment, including high computational costs, complex deployment pipelines, and the need for continuous adaptation to domain-specific data.

#### 1.3. Expectations

The system is expected to deliver higher-quality job recommendations to members and customers. Key user-facing expectations include:
*   **Responsiveness**: Job posters expect their new postings to be indexed and recommended almost immediately.
*   **Timeliness**: Members expect their job recommendations and search results to instantly reflect recent updates to their profiles or resumes.
To meet these expectations, the system must update embeddings in a timely manner, with changes reflected within seconds.

#### 1.4. Previous work

The previous-generation embedding platform at LinkedIn was named **Pensieve**. JUDE was designed to be an enhancement over Pensieve, addressing several of its limitations:
*   **Operational Inefficiency**: The previous system was harder to maintain.
*   **Feature Dependency**: It relied on standardized features, imprecise smaller ML models, and hard-to-maintain taxonomies, which are now replaced by LLM-derived representations.
*   **Architectural Issues**: It used a Lambda architecture, which led to "time-travel issues" (feature-label inconsistency) and required monitoring and recovery of failed scheduled inference jobs. JUDE migrates to a Kappa architecture to resolve these problems.

#### 1.5. Usage volumes and patterns

The system operates at LinkedIn's scale, which includes:
*   Over 1 billion registered members.
*   Tens of millions of active job postings.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Improve Recommendation Quality**: Increase key business metrics such as Qualified Applications and Total Job Applications, while decreasing negative signals like "Dismiss to Apply".
*   **Improve Operational Efficiency**: Simplify maintenance and reduce operational overhead compared to the previous system (Pensieve).
*   **Architectural Simplification**: Move from a Lambda to a Kappa architecture to resolve data consistency issues ("time-travel") and simplify the processing pipeline.
*   **Cost Efficiency**: Implement a cost-efficient GPU inference strategy with a nearline-first approach.
*   **Unified Representation**: Generate high-quality, transferable embeddings for jobs, member profiles, and resumes that can be used across the entire job recommendation stack.
*   **Low Latency Updates**: Ensure embeddings for new or updated entities are generated and served within seconds.

#### 2.2. Anti-goals

*   **Avoid Prohibitive Inference Costs**: The system intentionally avoids using cross-encoder models for online serving, despite their superior performance, due to significantly higher computational requirements. The chosen two-tower architecture with distillation is a deliberate trade-off for efficiency.

### 3. Risks and constraints

*   **Computational Cost**: Training and serving large (7B+ parameter) models at scale is computationally expensive. The design incorporates numerous optimizations (LoRA, Flash Attention 2, mixed precision, intelligent change detection) to manage GPU costs.
*   **Deployment Complexity**: Integrating LLMs into a production recommendation system involves complex pipelines for fine-tuning, real-time generation, and serving.
*   **Domain Adaptation**: General-purpose LLMs may not understand the specific dynamics and terminology of the job marketplace. The system requires a robust fine-tuning process to adapt models to LinkedIn's domain.
*   **Data Privacy**: The system must leverage proprietary LinkedIn data for fine-tuning while preserving member privacy. The article notes that dataset references are confined to the context of inference and first-party data is used to improve model effectiveness and support safety, security, and compliance.
*   **Scale**: The system must handle over 1 billion member profiles and tens of millions of job postings, requiring highly scalable infrastructure for both batch bootstrapping and real-time inference.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   The system's performance was evaluated against the **MTEB (Massive Text Embedding Benchmark)**.
*   An internal comparison was made between the chosen two-tower architecture and a more powerful cross-encoder model to quantify the performance gap.

#### 4.2. Online/business metrics

The online A/B test results from replacing standardized features with JUDE embeddings in L2 ranking models were:
*   **Qualified Applications**: +2.07%
*   **Dismiss to Apply**: -5.13%
*   **Total Job Applications**: +1.91%
This was noted as the highest metric improvement from a single model change for the team during that half-year period.

#### 4.3. Loss functions

The model's fine-tuning process uses a combination of three complementary loss functions:
*   **Binary Cross-Entropy Loss**: For the core classification task of predicting job application probability.
*   **Contrastive InfoNCE Loss**: Commonly used for retrieval and semantic search tasks to improve the quality of embeddings.
*   **VP-matrix Loss**: Provides robust outlier handling and effective utilization of weak convergence mechanisms.

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Primary Entities**: The system generates embeddings for three main text sources:
    1.  **Job Postings**: Job descriptions.
    2.  **Member Profiles**: Textual information from member profiles.
    3.  **Member Resumes**: Text from member resumes.
*   **Supervision Data**: Proprietary LinkedIn data, including user engagement signals (e.g., job applications) and human-annotated relevance labels.
*   **Changelogs**: Input Kafka/Brooklin streams provide changelogs for each entity, triggering nearline inference.

#### 5.2. Labeling strategy

A dual-signal supervision approach is used for fine-tuning:
*   **Relevance Labels**: Semantically oriented labels that enforce strict matching of role, location, and qualifications. They are high-quality but scarce, obtained through human annotation or foundation LLM evaluation with prompt engineering. These are used in initial training phases to establish baseline semantic understanding.
*   **Engagement Labels**: Labels derived from user behavior, such as job applications. They are available at a larger scale but can be noisy. They are used to align the model with real-world user preferences and business outcomes.

#### 5.3. Data quality issues and cleaning/enrichment

*   Engagement labels are acknowledged as being "potentially noisy".
*   To reduce redundant computation, a change detection mechanism is used to skip inference if the text content has not changed meaningfully. This is based on hashing text content. This optimization reduces nearline inference costs by up to 3x and offline bootstrapping inference volume by approximately 6x.

#### 5.4. ETL / Feature store

*   **Architecture**: The system uses a **Kappa architecture**.
*   **Nearline**: Real-time processing pipelines built with **Samza** consume changelog events from **Kafka/Brooklin** streams.
*   **Offline**: Embeddings generated in nearline are published to Kafka topics, which are then ETL'd to **HDFS** for use in model training.
*   **Training Data Generation**: **Spark** is used with time-aware joins to fetch the correct point-in-time embeddings for historical observation data.

### 6. Validation schema

#### 6.1. Train/validation/test split

[NO INFO]

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets

[NO INFO]

#### 6.4. Leakage risks and mitigation

The migration from a Lambda to a Kappa architecture was explicitly done to resolve "time-travel issues," which are a form of data leakage where training features contain information from the future relative to the label. The new architecture ensures that features reflect the same state as the underlying data when the database changes were made.

### 7. Baseline solution

*   **Previous System (Pensieve)**: The primary baseline is the previous-generation embedding platform, which relied on:
    *   Standardized features.
    *   Imprecise smaller ML models.
    *   Hard-to-maintain taxonomies.
    JUDE's LLM-based embeddings replaced these components.
*   **Architectural Baseline (Cross-Encoders)**: During development, a cross-encoder model was used as a performance baseline. Cross-encoders demonstrated superior performance but were too computationally expensive for production serving. The final two-tower model was distilled from a cross-encoder, bridging 50% of the performance gap while maintaining efficiency.

### 8. Errors and their analysis

*   **Architectural Trade-offs**: There is an acknowledged performance gap between the chosen two-tower architecture and a more powerful cross-encoder model. To mitigate this, offline cross-encoder distillation was implemented, which recovered 50% of the performance gap.
*   **Previous System Errors**: The prior Lambda architecture suffered from "time-travel issues" and required manual intervention for failed scheduled inference jobs. The Kappa architecture in JUDE was designed to eliminate these systemic problems.
*   **Noisy Labels**: Engagement-based labels (e.g., clicks, applications) are known to be potentially noisy, which can affect model training. This is balanced by using high-quality, semantically-oriented relevance labels.

### 9. Training pipelines

#### 9.1. Tooling

*   **Frameworks**: PyTorch, Hugging Face Transformers.
*   **Distributed Training**: DeepSpeed (specifically ZeRO stage 1 for optimizer state partitioning).
*   **Hardware**: Multi-node, multi-GPU training on NVIDIA H100 GPUs.
*   **Optimization Libraries**: Flash Attention 2, custom CUDA kernels from Liger.
*   **Orchestration (for bootstrapping)**: Flyte, Spark, Kubernetes, Ray.

#### 9.2. Training process

*   **Model Architecture**: A shared base LLM (7B+ parameters) with a shared tokenizer. Specialized prompt templates are used as soft task descriptors for different input types (jobs, profiles, resumes).
*   **Fine-tuning Method**: LoRA (Low-Rank Adaptation) is applied to the Query-Key-Value matrices in the Transformer attention blocks for parameter-efficient fine-tuning.
*   **Optimization Techniques**:
    *   **Memory/Speed**: Bfloat16 mixed precision, Flash Attention 2.
    *   **Memory vs. Compute Trade-off**: Gradient checkpointing is used to recompute intermediate activations during the backward pass.
    *   **Batch Size**: Gradient accumulation is used to achieve a large effective batch size.
*   **Optimizer**: AdamW with a slanted triangular learning rate schedule (warmup followed by cosine decay).
*   **Deployment**: Fine-tuned models are deployed in **Model Cloud**, LinkedIn's model inference stack.

### 10. Features

#### 10.1. Feature categories

*   **Primary Features**: Dense vector embeddings generated by a fine-tuned LLM. These embeddings represent the semantic meaning of text from:
    *   Job descriptions
    *   Member profiles
    *   Member resumes
*   **Interaction Features**: The top layers of the downstream models are intentionally lightweight, using simple feature interactions like crossing or stacked non-linear transformations. For Mistral family models, the Hadamard product was found to be beneficial for combining embeddings.

#### 10.2. Feature store / computation

*   **Generation**: Embeddings are generated via a nearline-first system built on a Kappa architecture.
*   **Online Storage**: Generated embeddings are stored in **Venice**, a high-performance key-value store, for real-time access by ranking models.
*   **Offline Storage**: Embeddings are also published to Kafka and ETL'd to **HDFS** for offline model training and analysis.
*   **Bootstrapping**: An on-demand system using Flyte/Spark/K8S/Ray performs one-time batch inference to bootstrap embeddings for all historical entities. It also supports targeted backfilling by time window or ID subset.

#### 10.3. Feature selection

The core principle is to let the fine-tuned LLM handle the heavy lifting of semantic understanding. The embeddings produced by the LLM replace a suite of older features (standardized features, outputs of smaller models, taxonomies). Downstream models use these embeddings directly with minimal additional feature engineering.

### 11. Measuring results

#### 11.1. Offline evaluation

*   The quality of the embeddings is benchmarked using the **MTEB** benchmark.
*   Internal experiments compared the performance of the final two-tower architecture against a cross-encoder baseline to measure the effectiveness of distillation.

#### 11.2. A/B test design

*   **Hypothesis**: Replacing existing standardized features in the job recommendation and search L2 ranking models with JUDE embeddings will improve recommendation quality.
*   **Methodology**: The new embeddings were ramped online in an A/B test.
*   **Primary Metrics**:
    *   Qualified Applications
    *   Dismiss to Apply
    *   Total Job Applications
*   **Decision**: The change was rolled out after observing a +2.07% increase in Qualified Applications, a -5.13% decrease in Dismiss to Apply, and a +1.91% increase in Total Job Applications.

#### 11.3. Reporting

[NO INFO]

### 12. Integration and Serving

#### 12.1. API design

*   The fine-tuned LLM is hosted as a microservice in LinkedIn's **Model Cloud**.
*   It exposes a **GRPC endpoint** for embedding inference, which is called by the nearline processing pipelines.

#### 12.2. Infrastructure

*   **Serving Cluster**: The model is hosted in a **Model Serving cluster**, replicated across multiple **Kubernetes deployment GPU pods** for scalability.
*   **Real-time Processing**: **Samza** pipelines process change events from **Kafka/Brooklin** streams.
*   **Online Storage**: **Venice** (key-value store) serves embeddings to downstream ranking models.
*   **Offline Storage**: **HDFS** stores embeddings for batch use cases.
*   **Batch Bootstrapping**: A pipeline orchestrated by **Flyte/Spark/K8S/Ray**.

#### 12.3. SLAs and Fallback

*   **Latency**: For a 7B LLM, embedding inference latency is under **300ms at the p95 quantile**.
*   **Data Freshness**: Changes to jobs, profiles, and resumes are reflected in the system "within seconds".
*   **Fallback Strategy**: [NO INFO]

#### 12.4. Release cycle

[NO INFO]

### 13. Monitoring

*   **Input Monitoring**: A change detection mechanism based on hashing text content is implemented to monitor for meaningful changes. This reduces inference load by skipping unchanged inputs.
*   **System Health**: The previous system's pain point of monitoring and recovering failed scheduled inference jobs was a key driver for the new architecture, suggesting that the Kappa-based system is simpler to monitor and more resilient.
*   **Data/Model Quality Monitoring**: [NO INFO]
*   **Engineering Metrics Monitoring**: [NO INFO]
*   **Alerting and Tooling**: [NO INFO]

### 14. Operations

*   **Retraining Cadence**: [NO INFO]
*   **Operational Procedures**:
    *   **Bootstrapping**: A well-defined, on-demand system exists for a one-time batch inference to create the initial set of embeddings for all historical entities.
    *   **Backfilling**: The same system supports targeted historical embedding generation for specific time windows or entity ID subsets, ensuring complete feature coverage for model training.
    *   **Nearline Updates**: After bootstrapping, the nearline inference system is treated as the source of truth for all future updates.
*   **Incident Response and Rollback**: [NO INFO]
*   **Non-engineering Considerations**: The future work section mentions plans to incorporate members' job-seeking activity data to enrich semantic understanding, indicating ongoing product and model evolution.