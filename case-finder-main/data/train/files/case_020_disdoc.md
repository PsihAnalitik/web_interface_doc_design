**Company**: Criteo
**Title**: Improving Consistency Models with Generator-Augmented Flows
**Technology area**: Predictive ML
**Source URL**: https://medium.com/criteo-engineering/improving-consistency-models-with-generator-augmented-flows-abc2ae135506
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The core business problem is the real-time generation of personalized ad creatives (images and videos) at a large scale. The technical challenge stems from the limitations of existing generative models. Classic diffusion-based generators produce high-quality samples but require dozens of iterative steps for inference, making them too slow for real-time ad personalization and large-scale deployment.

Consistency Models (CMs) have emerged as a faster alternative, promising high-speed inference. However, they suffer from significant training instability, particularly when trained from scratch without a pre-trained teacher model. This project, titled "Improving Consistency Models with Generator-Augmented Flows," originates from Criteo's R&D AI Foundations team to address this training instability and unlock the potential of fast generative models for production use.

#### 1.2. Relevance & reasons

The primary business driver is to enhance ad personalization to boost user engagement. By generating diverse and high-quality ad variations in real-time, Criteo can deliver more relevant content to users.

A secondary driver is the reduction of operational costs. The proposed solution aims to speed up model training and convergence, which would lead to a significant reduction in GPU consumption for both training and fine-tuning generative models.

#### 1.3. Expectations

The system is expected to generate high-quality, diverse ad variations quickly enough for real-time serving. The solution should improve upon existing one-step Consistency Models by providing more stable training and better final performance.

#### 1.4. Previous work

-   **Classic Diffusion-based Generators**: These models are considered the state-of-the-art in terms of generation quality. However, their iterative nature (requiring dozens of steps) makes them unsuitable for Criteo's real-time personalization use case due to high latency.
-   **Consistency Models (CMs)**: These models are a known alternative that promises fast, one-step inference. However, they have a major drawback: training instability. The article highlights two training modes for CMs:
    1.  **Distillation-based**: Training by imitating a pre-trained diffusion model. This is considered the "ideal setting" but requires the preliminary, costly step of training a full diffusion model.
    2.  **"From Scratch"**: Training without a pre-trained model. This is an appealing option as it is more direct, but it is the mode that suffers from training instability.

#### 1.5. Usage volumes and patterns

The system is intended for "large-scale inference pipelines," but specific QPS or data volume metrics are not provided.

### 2. Goals and anti-goals

#### 2.1. Goals

-   **Improve Training Stability**: The primary goal is to solve the training instability observed in Consistency Models when trained "from scratch."
-   **Boost Model Performance**: Improve the final quality of the generated images/videos compared to baseline "from scratch" CMs.
-   **Accelerate Convergence**: Speed up the training process to enable quicker iteration, fine-tuning, and deployment.
-   **Reduce Infrastructure Costs**: Lower GPU consumption during training and inference.
-   **Enable Real-Time Inference**: The final model must be a fast, one-step generator suitable for real-time ad personalization.

#### 2.2. Anti-goals

-   **Avoid Multi-Step Inference**: The solution must not rely on the slow, iterative inference process characteristic of classic diffusion models.
-   **Avoid Reliance on Pre-trained Models**: The solution should improve the "from scratch" training regime, removing the dependency on having a pre-trained diffusion model for distillation.

### 3. Risks and constraints

-   **Technical Risk**: The primary risk identified is the inherent training instability of Consistency Models when trained from scratch. The research aims to mitigate this directly.
-   **Latency Constraint**: The system must operate in real-time to serve personalized ads, imposing a strict latency budget on the generation process.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

[NO INFO]

#### 4.2. Online/business metrics

-   **User Engagement**: The ultimate business goal is to boost user engagement with the generated personalized ads.

#### 4.3. Loss functions

The core innovation of this work lies in modifying the training process of "from scratch" Consistency Models. The analysis identified an "extra regularisation term on the generator" that appears during "from scratch" training, causing it to deviate from the ideal distillation setting and leading to instability.

The proposed solution, **Generator-Augmented Flows (GC)**, introduces a fix to the training loss. It creates a self-reinforcement loop by modifying the data-noise coupling that defines the training loss. Specifically, the model's own endpoint predictions are fed back into this coupling. This is designed to reduce the gap between the "from scratch" and distillation training settings, thereby improving stability and performance.

### 5. Data (Dataset)

#### 5.1. Data sources

[NO INFO]

#### 5.2. Labeling strategy

[NO INFO]

#### 5.3. Available metadata

[NO INFO]

#### 5.4. Data quality issues and cleaning

[NO INFO]

#### 5.5. ETL

[NO INFO]

### 6. Validation schema

#### 6.1. Train/validation/test split

[NO INFO]

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets

[NO INFO]

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

The primary baseline for this work is the **"from scratch" Consistency Model (CM)**. This model is chosen because it offers the promise of fast, one-step inference without the need for a pre-trained diffusion model, but it suffers from poor training stability.

The performance of this baseline is implicitly compared to two other points of reference:
1.  **Distillation-based CM**: This is considered the "ideal setting" for CM training, providing a performance ceiling that the "from scratch" model fails to reach.
2.  **Classic Diffusion Models**: These serve as the quality benchmark but are considered too slow for the target application.

The goal of the proposed Generator-Augmented Flows is to elevate the performance and stability of the "from scratch" CM to be closer to the distillation-based CM.

### 8. Errors and their analysis

The central error analysis focuses on the training dynamics of Consistency Models.

-   **Error Type**: Training instability and suboptimal final performance in "from scratch" CMs.
-   **Root Cause Analysis**: The authors performed a comparative analysis between the "distillation" and "from scratch" training settings. They identified a key discrepancy: when a CM is trained from scratch, an "extra regularisation term on the generator" emerges. This term deviates the training process from the ideal distillation setting and is identified as the cause of the training instabilities.
-   **Proposed Solution**: The "Generator-Augmented Flows" (GC) technique was designed specifically to reduce this gap. By feeding the model's own endpoint predictions back into the training loss, it lowers the stochasticity during training and better aligns the "from scratch" process with the more stable distillation setting.

### 9. Training pipelines

#### 9.1. Tooling

The article mentions training is performed on GPUs but does not specify frameworks (e.g., PyTorch, TensorFlow) or other tooling.

#### 9.2. Training process

The work focuses on improving the "from scratch" training mode for Consistency Models. The proposed **Generator-Augmented Flows (GC)** method modifies this process with a self-reinforcement mechanism:

1.  During a training step, the model makes an endpoint prediction.
2.  This prediction is fed back into the data-noise coupling that defines the training loss for that same step.
3.  This loop acts as a guide, using the model's own outputs to stabilize learning and reduce the discrepancy with the ideal distillation setting.

This approach is designed to speed up convergence and boost the final performance of the model.

#### 9.3. Experiment tracking

[NO INFO]

### 10. Features

[NO INFO]

### 11. Measuring results

#### 11.1. Offline evaluation

The article states that the method "boost[s] final performance," but does not specify the offline evaluation metrics (e.g., FID, Inception Score) used to quantify this improvement.

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting

[NO INFO]

### 12. Integration and Serving

#### 12.1. API design

The system is intended for "real-time ad personalization," which implies an online serving architecture with a low-latency API. The model is a one-step generator, which is architecturally suited for this requirement.

#### 12.2. Infrastructure

-   **Inference**: The system is designed for "large-scale inference pipelines."
-   **Hardware**: The discussion around reducing "GPU consumption" suggests that both training and inference are intended to run on GPUs.

#### 12.3. SLAs and fallback strategies

-   **SLAs**: A strict real-time latency budget is a core requirement, but specific millisecond targets are not provided. The key constraint is being significantly faster than the "dozens of iterative steps" required by classic diffusion models.
-   **Fallback Strategies**: [NO INFO]

### 13. Monitoring

#### 13.1. Data quality

[NO INFO]

#### 13.2. Model quality

[NO INFO]

#### 13.3. Input/target drift

[NO INFO]

#### 13.4. Engineering metrics

[NO INFO]

#### 13.5. Alerting and tooling

[NO INFO]

### 14. Operations

#### 14.1. Retraining cadence

The proposed method leads to "quicker training and fine-tuning," which would enable a more frequent or less costly retraining cadence. However, a specific schedule is not mentioned.

#### 14.2. Incident response

[NO INFO]

#### 14.3. Non-engineering considerations

[NO INFO]