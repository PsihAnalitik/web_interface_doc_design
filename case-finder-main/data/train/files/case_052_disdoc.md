**Company**: Lifen
**Title**: Visual Explainable NLP @ Lifen
**Technology area**: NLP, MLOps, Explainable AI (XAI)
**Source URL**: https://medium.com/lifen-engineering/visual-explainable-nlp-lifen-4d4dd5007205
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

Lifen's machine learning models, primarily in Natural Language Processing (NLP), serve over 1 million predictions daily. This high volume generates support requests from users when the AI makes an incorrect or counterintuitive prediction. The problem was to provide internal teams, specifically Data Scientists and Customer Support, with a tool to efficiently investigate these cases.

The solution is an internal web application named `lifen-ai-explainer`. Given a `document id` from a support request, the application displays the anonymized document and the predictions the AI made on the original, non-anonymized document.

#### 1.2. Relevance & reasons

The primary goal is to streamline the support process for ML model predictions. Before this tool, investigating prediction errors was likely an ad-hoc, manual process. The `lifen-ai-explainer` system provides a standardized and accessible way to get insights into why a model made a specific prediction. This is crucial for debugging real-world issues, such as understanding how a typo or a misread word in a document led to a wrong prediction. The system has been integrated into daily workflows since mid-2020.

#### 1.3. Expectations

The system is expected to:
- Be easily accessible to authorized internal users (Data Scientists, Customer Support).
- Provide visual explanations for model predictions to give insight into the model's reasoning.
- For text classification, it should highlight the words that most influenced the prediction.
- For Named Entity Recognition (NER), it should show the raw softmax scores for each token and class.
- Always remain up-to-date with the main production AI system (`lifen-ai`).
- Handle data privacy by displaying an anonymized version of the document.

#### 1.4. Previous work

The `lifen-ai-explainer` application and its associated pseudonymisation algorithm were developed internally to address the lack of a streamlined support and debugging tool.

#### 1.5. Usage volumes and patterns

The main production system, `lifen-ai`, handles over 1 million predictions daily. The `lifen-ai-explainer` tool is used on-demand by internal teams to investigate specific support cases identified by a `document id`.

### 2. Goals and anti-goals

#### 2.1. Goals

- **Streamline Support:** Reduce the time and effort required to investigate user-reported prediction errors.
- **Provide Explainability:** Offer insights into how the ML models work, moving beyond black-box predictions.
- **Maintainability:** Ensure the tool is easy to maintain and evolves in lockstep with the production AI models.
- **Accessibility:** Make explainability tools easily accessible to non-ML expert teams like Customer Support.
- **Debuggability:** Enable developers and data scientists to debug specific model behaviors, such as NER post-processing or classification logic.

#### 2.2. Anti-goals

- **Real-time End-User Explanations:** The tool is designed for internal support and debugging, not for providing real-time explanations to the end-users of the primary application.
- **Using Resource-Intensive Models:** The underlying prediction models intentionally avoid Transformer architectures due to constraints related to long documents, resources, and time. The explainability solution must work with the existing Embedding+LSTM architecture.

### 3. Risks and constraints

#### 3.1. Risks

- **Synchronization Drift:** The primary risk is that `lifen-ai-explainer` could become out of sync with the production `lifen-ai` system, leading to an inability to debug new features or models. A breaking change in `lifen-ai` could render the explainer tool useless. This risk is actively mitigated through a mono repo and CI/CD strategy.
- **Poor Encapsulation:** A risk of building the explainer on top of the main application is creating circular dependencies or tightly coupled code, making both systems harder to maintain. This is mitigated using tools like `import-linter`.

#### 3.2. Constraints

- **Model Architecture:** The production models use an Embedding + LSTM architecture. This architecture is not inherently explainable, requiring modifications (like adding an attention layer) to enable interpretability.
- **Data Privacy:** Due to the sensitive nature of the documents, the system must display a pseudonymised version. However, to be useful, it must show predictions generated from the original, unaltered document, as the anonymization process itself could change the model's output.
- **Internal Use:** The tool is for internal use only, which dictates its feature set and access control.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The article notes that the attention scores used for explainability "proved empirically very interpretable," suggesting qualitative evaluation by data scientists. No quantitative or formal metrics for measuring the quality of explanations are mentioned.

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

The models use a `softmax` layer for classification, which implies a categorical cross-entropy loss function. No other details on loss functions are provided.

### 5. Data (Dataset)

#### 5.1. Data sources

The system processes documents from the main `lifen-ai` application. The input to the `lifen-ai-explainer` is a `document id` corresponding to a document that has already been processed by the production models.

#### 5.2. Labeling strategy

The system has been extended to include a "dataset labellisation interface" and a "post-training errors review tool," suggesting a human-in-the-loop process for data labeling and error correction. However, the specifics of this process are not detailed.

#### 5.3. Data quality issues

The tool is designed to help identify data quality issues that affect model performance, such as:
- Typos
- Misread words from OCR [inferred]
- Misplaced words

#### 5.4. Data processing

A critical step is the internal pseudonymisation algorithm. The process is as follows:
1. A `document id` is provided.
2. The original document is retrieved.
3. The production `lifen-ai` model runs prediction on the **original** document.
4. The original document is passed through a pseudonymisation algorithm to create an anonymized version.
5. The web application displays the **anonymized** document alongside the **original** predictions.

### 6. Validation schema

[NO INFO]

### 7. Baseline solution

The baseline model architecture for classification was a standard Embedding + LSTM, which used the last hidden state for prediction. This approach was not suitable for explainability because it was impossible to determine which input tokens contributed most to the final prediction. It also suffered from potential vanishing gradient and information bottleneck issues with long sequences.

The baseline support process was an ad-hoc, manual investigation without a dedicated tool.

### 8. Errors and their analysis

The `lifen-ai-explainer` tool is fundamentally an error analysis platform. It provides two main modes for analysis:

- **Classification Error Analysis:**
    - The system uses a global attention mechanism to generate "importance scores" (attention weights) for each word.
    - In the UI, words are highlighted based on these scores, visually indicating which parts of the text most influenced the classification decision (e.g., for document type or patient gender). This helps users quickly spot if the model focused on an irrelevant or incorrect word.

- **NER Error Analysis:**
    - The tool provides a detailed view for debugging NER models.
    - It displays the final, post-processed entity predictions.
    - Crucially, it also shows the raw `softmax` output from the model for each token, revealing the score for every possible class. This allows developers to distinguish between errors originating from the core model versus errors introduced during the post-processing step.

### 9. Training pipelines

[NO INFO]

### 10. Features

The features for the NLP models are word embeddings learned from the text. The explainability feature is derived from a model architecture modification.

- **Global Attention Layer:** To enable explainability, a global attention layer (attentive pooling) was added to the baseline LSTM model. This layer computes a weighted sum of the LSTM hidden states from all timesteps.
    - An attention score is computed for each token using a dense layer followed by a softmax.
    - These scores are used to weigh the hidden states.
    - The resulting weighted sum is a single vector embedding representing the entire document, which is then used for classification.
- **Explainability "Features":** The attention scores themselves are a by-product of this architecture. They are extracted and interpreted as "importance scores" for each word, serving as the basis for the visual explanations.
- **Multi-Head Attention:** In practice, the implementation uses multiple attention heads to improve performance, though this can make interpretation more complex. The layer is implemented in Keras.

```python
def MultiGlobalAttention(timesteps: tf.Tensor, n_heads: int = 1) -> tf.Tensor:
    """Global Attention layer. Computes a weighted sum of all the timesteps.
    Input: N timesteps of dim D
    Output: 1 of dim D
    Zhou et al https://www.aclweb.org/anthology/P16-2034 §3.3"""
    attention = Dense(n_heads, use_bias=False, activation="linear")(timesteps)
    attention = Activation(softmax_axis(1), name="attention")(attention)
    weighted_sum = dot([attention, timesteps], axes=1)
    return Flatten()(weighted_sum)
```

To get the scores for explainability, a sub-model is created that specifically extracts the output of the attention layer. This is only run in the `lifen-ai-explainer` context, not during standard inference.

```python
def attention_model(model: Model) -> Model:
    """make attention_model from model"""
    return Model(inputs=model.input, outputs=model.get_layer("attention").output)
```

### 11. Measuring results

[NO INFO]

### 12. Integration and Serving

The `lifen-ai-explainer` is a full-stack web application with a clear architecture designed for maintainability and synchronization with the main AI system.

#### 12.1. System Architecture

- **Frontend:** A React Single-Page Application (SPA) written in TypeScript. It uses Vite for build tooling.
- **Backend:** A Python REST API built with FastAPI. The backend serves the static frontend files and provides the data API.
- **`lifen-ai` Integration:** The `lifen-ai-explainer` backend is a Python application that imports the production `lifen-ai` system as a library. This allows the explainer to call the exact same prediction code that runs in production.

#### 12.2. API and Client Generation

- The FastAPI backend automatically generates an OpenAPI specification.
- The frontend TypeScript client is automatically generated from this OpenAPI spec using Orval. This ensures that any breaking change in the API response format will cause the frontend build to fail, immediately flagging the need for an update.

#### 12.3. Synchronization and Encapsulation Strategy

- **Mono Repo:** Both `lifen-ai` and `lifen-ai-explainer` reside in the same Git repository. This enables atomic commits and pull requests that modify both systems simultaneously, enforcing synchronization.
- **CI/CD Enforcement:** The continuous integration pipeline is set up so that a breaking change in `lifen-ai`'s API or types will cause the `lifen-ai-explainer` build to fail. This forces developers to update the explainer before merging changes to the main AI system.
- **Static Typing:** The entire Python codebase is 100% type-annotated and checked with `mypy`, which helps catch integration issues at build time.
- **Dependency Management:**
    - Poetry is used for Python dependency management. It is configured with dependency groups to manage the relationship.
    - `lifen-ai-explainer` includes all dependencies of `lifen-ai`.
    - `lifen-ai` does *not* include the dependencies of `lifen-ai-explainer`.
- **Code Encapsulation:** The `import-linter` tool is used to enforce architectural boundaries. It is configured to allow `lifen-ai-explainer` to import from `lifen-ai`, but strictly forbids `lifen-ai` from importing anything from `lifen-ai-explainer`.

### 13. Monitoring

The `lifen-ai-explainer` system itself serves as a tool for qualitative, case-by-case monitoring of model prediction quality. The article does not describe monitoring for the explainer application itself (e.g., uptime, latency, error rates).

### 14. Operations

- **Workflow:** The tool has been fully integrated into daily operations for Data Scientists and Customer Support since mid-2020. When a support request about a specific prediction arises, the user takes the `document id`, enters it into the `lifen-ai-explainer` web app, and uses the visual explanations to diagnose the issue.
- **Maintenance:** Maintenance is enforced by the mono repo and CI/CD setup. Any developer adding a new prediction feature to `lifen-ai` is required to simultaneously add the corresponding visualization and debugging support to `lifen-ai-explainer` within the same pull request.
- **System Evolution:** The platform has been extended beyond its initial scope to include a "dataset labellisation interface" and a "post-training errors review tool," making it a more comprehensive MLOps platform.