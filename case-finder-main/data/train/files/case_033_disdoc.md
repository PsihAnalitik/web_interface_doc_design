**Company**: Replit
**Title**: Building LLMs for Code Repair
**Technology Area**: Generative AI & LLM
**Source URL**: https://blog.replit.com/code-repair
**Content Type**: article

### 1. Problem definition

#### 1.1. Origin

The project's goal is to create a "Replit-native" AI model that automatically repairs code errors within the Replit IDE. This is part of a broader company vision to make AI a first-class citizen of the development environment by tightly integrating AI tools with the IDE. The model is designed to take a session event, specifically a Language Server Protocol (LSP) diagnostic, as input and produce a code fix as a well-defined response.

#### 1.2. Relevance & reasons

Developers spend a significant portion of their time fixing bugs. Replit has supported the Language Server Protocol (LSP) since 2018, which helps users find errors in their code. This results in hundreds of millions of LSP diagnostic events per day, making them one of the most common events on the platform.

However, while the LSP is effective at identifying errors, it provides automated fixes (CodeActions) in limited cases. For Python projects on Replit, only 10% of LSP diagnostic messages have an associated fix. This leaves a large gap where developers must manually resolve errors. The abundance of `(code, diagnostic)` data makes this an ideal scenario for building an AI model to automate code repair.

#### 1.3. Expectations

The primary expectation is to develop a useful tool for Replit developers that can automatically suggest fixes for code errors that the LSP cannot handle. The model's output should be a code diff that can be applied directly in the IDE. The system must also meet latency and cost constraints suitable for a real-time developer tool.

#### 1.4. Previous work

The existing system relies on the Language Server Protocol (LSP). The LSP server analyzes code and generates diagnostics (errors, warnings). For a small fraction of these diagnostics (10% in Python), the LSP also provides a deterministic `CodeAction` which is a pre-defined fix. The proposed ML system is designed to address the 90% of cases where no `CodeAction` is available.

#### 1.5. Usage volumes and patterns

The system processes hundreds of millions of LSP diagnostic events per day across all users on the Replit platform. The initial focus is on Python projects.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Automate Code Repair:** Automatically generate code fixes for LSP diagnostics that do not have a deterministic `CodeAction`.
*   **Replit-Native Integration:** Build a model that is native to the Replit environment, consuming IDE events (LSP diagnostics) and producing environment-compatible outputs (code diffs).
*   **High-Quality Fixes:** The generated fixes should be functionally correct and consistently formatted.
*   **Efficiency:** The model must be small enough (7B parameters) to meet inference latency and cost constraints for a real-time user-facing feature.
*   **State-of-the-Art Performance:** The 7B parameter model should be competitive with much larger, general-purpose models like GPT-4 Turbo on the code repair task.

#### 2.2. Anti-goals

*   **Do not replace deterministic fixes:** The system will not be used for diagnostics where the LSP already provides a `CodeAction`. The deterministic solution will always be preferred.
*   **Do not fix stylistic issues:** The model is not intended to fix stylistic rules, such as line length (`ruff[E501]`) or unsorted imports (`ruff[I001]`). These are explicitly filtered out.
*   **Avoid complex output formats:** The model should not generate Unified Diffs, as experiments showed they were prone to hallucinating line numbers and had higher decoding costs. The chosen format is the simpler and more constrained Numbered Line Diff.

### 3. Risks and constraints

#### 3.1. Risks

*   **Evaluation Data Leakage:** Many public program repair benchmarks are known to be present in the pre-training corpora of SOTA LLMs, making them unsuitable for accurate evaluation. This was mitigated by creating custom evaluation sets from recent, held-out data.
*   **Mode Collapse in Data Synthesis:** Synthesizing training data (both buggy code and fixes) from scratch can lead to mode collapse. This risk was mitigated by starting from real-world buggy code states and only synthesizing the corresponding fix.
*   **Model Hallucination:** The model could generate incorrect or malformed diffs, such as hallucinating line numbers or content. This is mitigated through data verification steps and by choosing a constrained output format.

#### 3.2. Constraints

*   **Latency and Cost:** The choice of a 7B parameter model was driven by the need to balance model capabilities with inference latency and cost constraints for a production service.
*   **Output Format:** The model's output must be a consistently formatted and parseable Numbered Line Diff to allow for unambiguous, programmatic application in the IDE.
*   **Data Scope:** The initial model is constrained to public, non-private Python projects on Replit.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Functional Correctness:** Measures the functional equivalence of the model-fixed code against the ground-truth fixed code. This is evaluated by executing the code against a set of test cases. This metric is only used for the *Leetcode repair eval* where test cases are available.
*   **Exact Match:** Used as a proxy for correctness when test cases are not available. It is considered a lower bound on functional correctness.
    *   **AST Match:** Compares the Abstract Syntax Tree (AST) of the model-fixed code with the ground-truth AST.
    *   **AST Match String Fallback:** If either the source or fixed code cannot be parsed into a valid AST, the metric falls back to a direct string comparison. This handles cases where a fix is valid but the code snippet is not fully parsable.
*   **Pass@1:** All models are evaluated in a single-pass setting, reflecting a real-world deployment scenario.

#### 4.2. Online/business metrics

*   **User Acceptance/Rejection Rate:** [inferred] Future work plans to use user feedback on whether a suggested fix is accepted or rejected to further improve the model (e.g., via DPO). This implies that acceptance rate will be a key online business metric.

#### 4.3. Loss functions

*   **Cross-Entropy Loss:** [inferred] The model is finetuned as a standard auto-regressive language model, so the training objective is to minimize the cross-entropy loss for next-token prediction.

### 5. Data (Dataset)

#### 5.1. Data sources

*   **LSP Diagnostics:** Logged from all user sessions in BigQuery. Each entry includes `repl_id`, `error_timestamp`, `error_path`, `error_code`, `error_message`, and `error_range`. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_033/img_004.png`)
*   **Operational Transformations (OTs):** A stream of edit-by-edit changes for every file, allowing for the complete historical reconstruction of a project's state at any given timestamp.
*   **Repl Snapshots:** Regular snapshots of each project's most recent state, stored in Google Cloud Storage (GCS), used to verify the correctness of the OT-based file reconstruction.

#### 5.2. Labeling strategy

The training labels (correct diffs) are synthetically generated via a distillation process, as user-provided fixes were found to be noisier and have higher variance.

1.  **Select Real Errors:** Start with real `(code, diagnostic)` pairs from the BigQuery logs.
2.  **Synthesize Diffs:** Use large pre-trained code LLMs in a few-shot prompt pipeline (implemented with DSPy) to generate a numbered line diff that fixes the error.
3.  **Verify Diffs:** The synthesized diffs undergo a multi-stage verification process:
    *   **Format Check:** Regular expressions are used to extract diffs and filter out any malformed or incomplete outputs.
    *   **Applicability Check:** The system attempts to apply the generated diff to the source code to ensure it can be applied correctly and unambiguously. Samples that fail due to incorrect line numbers or hallucinated content are discarded.
    *   **Correctness Filtering:** An LLM is prompted to filter out diffs that are syntactically valid but semantically incorrect.

#### 5.3. Data quality issues and cleaning

*   **Data Filtering:** The initial dataset from BigQuery is filtered to exclude:
    *   Diagnostics with associated `CodeActions` (deterministic fixes).
    *   Stylistic rules (e.g., `ruff[E501]`, `ruff[I001]`).
    *   Private and non-Python projects.
*   **State Reconstruction Sanity Check:** The OT-based reconstruction process is validated by asserting that it can reproduce the most recent Repl filesystem, matching a snapshot stored in GCS.
*   **Diagnostic Verification:** After reconstructing a file state, `Ruff` and `pyright-extended` are run to assert that the expected set of diagnostics is reproduced. This verification is performed by a serverless lambda function that can scale up in bursts.

#### 5.4. ETL or feature store architecture

The data pipeline is implemented using PySpark on Databricks to handle large-scale data processing. The target was to create a dataset of 100k examples, with the pipeline designed to scale by at least another order of magnitude. The overall flow is:
1.  Log LSP diagnostics from user sessions to BigQuery.
2.  Use PySpark on Databricks to process these events.
3.  For each diagnostic, use OTs to reconstruct the full project filesystem at that specific timestamp.
4.  Synthesize and verify diffs using a DSPy pipeline and LLM verifiers.
5.  Store the final `(code, diagnostic, diff)` triplets as the training dataset.
(see image: `ml-design-doc-reviewer/data/raw_documents/images/case_033/img_002.png`)

### 6. Validation schema

#### 6.1. Train/validation/test split strategy

A held-out test set is created to evaluate the model. To prevent data leakage between the training and test sets:
*   **Repl-level Splitting:** The split is performed at the Repl (project) level, ensuring that all data from a single project belongs to only one split.
*   **Deduplication:** A deduplication procedure, as recommended by the StarCoder project, is applied to the data.

#### 6.2. Holdout sets and update frequency

Two distinct holdout sets (evaluation benchmarks) were created:

*   **Replit Repair Eval (Real-World Benchmark):**
    *   **Composition:** 389 samples of `(code, diagnostic)` pairs sampled from held-out Replit user data. Low-quality code (e.g., Python files containing only natural language) was removed.
    *   **Ground Truth:** Fixes were first generated by a SOTA LLM, then manually verified and corrected by a human annotator.
    *   **Purpose:** To test the model in its target inference setting, fixing real-world errors from users of diverse skill levels.

*   **Leetcode Repair Eval (Academic Benchmark):**
    *   **Composition:** 360 samples based on the DebugBench dataset, focusing on syntactic and reference errors where LSP diagnostics are helpful.
    *   **Recency:** To combat pre-training data leakage, the benchmark was augmented with recent problems from Leetcode competitions (after the base model's data cutoff date), using the synthetic bug injection pipeline from DebugBench.
    *   **Purpose:** To measure the model's performance on public benchmarks and compare it against other SOTA models.

#### 6.3. Leakage risks and how they are mitigated

The primary leakage risk is that public benchmark data may have been part of the base model's pre-training corpus. This was mitigated by:
1.  Creating the `Replit Repair Eval` from private, held-out user data.
2.  Augmenting the `Leetcode Repair Eval` with problems created after the base model's training data cutoff date.
3.  Using strict Repl-level splitting and data deduplication for the train/test sets.

### 7. Baseline solution

#### 7.1. Simple baselines

The implicit baseline is the existing system, which relies on the Language Server Protocol (LSP). This system can only provide automated fixes (`CodeActions`) for 10% of Python diagnostics, leaving the user to fix the remaining 90% manually.

#### 7.2. Comparison framework against advanced models

The finetuned `Replit Code Repair 7B` model is compared against a suite of SOTA LLM baselines on the two evaluation benchmarks:

*   **API-based Models:**
    *   GPT-4-Turbo (`gpt-4-0125-preview`)
    *   GPT-3.5-Turbo (`gpt-3.5-turbo-0125`)
    *   Claude-3-Opus (`claude-3-opus-20240229`)
    *   Claude-3-Haiku (`claude-3-haiku-20240307`)
*   **Open-source Model:**
    *   DeepSeek-Coder-Instruct-v1.5 (7B), the base model used for finetuning, evaluated in a zero-shot setting.

### 8. Errors and their analysis

#### 8.1. Error taxonomy by pipeline stage

*   **Data Synthesis:**
    *   **Malformed Diffs:** The synthesis LLM could produce text that is not a valid line diff. This is filtered out using regular expressions.
    *   **Inapplicable Diffs:** The LLM could hallucinate incorrect line numbers or content, making the diff impossible to apply. This is filtered by attempting to apply every synthesized diff.
    *   **Incorrect Diffs:** The diff could be applicable but not actually fix the bug. This is mitigated by using another LLM as a filter.
*   **Model Prediction:**
    *   The model can generate fixes that are not functionally correct, even if they are syntactically valid. This is captured by the "Functional Correctness" metric.
    *   The model can fail to produce a fix that exactly matches the ground truth, captured by the "Exact Match" metrics.

#### 8.2. Residual analysis

Analysis showed a significant performance gap between the two evaluation sets. The overall performance of all models, including `Replit Code Repair 7B`, was lower on the `Replit Repair Eval` (real-world data) compared to the `Leetcode Repair Eval` (academic benchmark). This demonstrates the difficulty of the real-world task and the importance of evaluating on data that reflects the production environment. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_033/img_006.jpg`)

### 9. Training pipelines

#### 9.1. Tooling

*   **Data Processing:** PySpark on Databricks, with a serverless lambda for diagnostic verification.
*   **Synthetic Data Generation:** DSPy for the few-shot synthesis pipeline.
*   **Training Framework:** A fork of MosaicML’s LLM Foundry (v0.5.0) using the Composer trainer.
*   **Experiment Tracking:** [inferred] LLM Foundry and the MosaicML platform provide experiment tracking capabilities.

#### 9.2. Preprocessing, training, evaluation, and deployment automation

*   **Preprocessing:**
    *   Input data is formatted into a custom schema using sentinel tokens (see Section 10).
    *   Sequences are packed using Bin Packing (with a ratio of 6.0, profiled using an LLM Foundry script) to improve training efficiency.
*   **Training:**
    *   **Base Model:** DeepSeek-Coder-Instruct-v1.5 (7B), with its architecture patched to use the Flash Attention v2 Triton kernel.
    *   **Infrastructure:** Training was performed on the MosaicML platform using a single node of 8x H100 GPUs per experiment.
    *   **Distributed Strategy:** FSDP (Fully Sharded Data Parallelism) with the `Full Shard` strategy and activation checkpointing.
    *   **Optimizer:** Decoupled AdamW (`lr=1e-5`, `beta_1=0.9`, `beta_2=0.99`, `epsilon=1e-8`, no weight decay).
    *   **Scheduler:** Cosine Annealing with a 100-batch warmup, decaying to 0.01x the initial learning rate.
    *   **Hyperparameters:** Batch size of 16, trained for 4 epochs. Gradient clipping with a norm-based threshold of 1.0.
    *   **Precision:** Training was done in mixed precision with BF16.

### 10. Features

#### 10.1. Feature categories and selection criteria

Instead of traditional feature engineering, the model uses a structured prompt format with sentinel tokens to delineate different pieces of information from the IDE. This approach was chosen over natural language instructions to ensure more consistent and parseable responses.

*   **Input Features:**
    *   `file_name`: The name of the file containing the error.
    *   `code`: The full content of the file, with line numbers prepended to each line.
    *   `lsp_error`: The error message string from the LSP diagnostic.
    *   `error_line`: The specific line of code that triggered the error.
*   **Output Target:**
    *   `diff`: A numbered line diff that corrects the error.

(see image: `ml-design-doc-reviewer/data/raw_documents/images/case_033/img_005.png`)

#### 10.2. Rationale for feature choices

*   **Sentinel Tokens (`<code>`, `<lsp_error>`, etc.):** This schema makes the model's output more reliable and easier to parse. It is also extensible for future work involving more complex IDE events (e.g., `<run_command>`).
*   **Line Numbers:** Added to the input code and used in the output diff. This was found to empirically boost response quality and guarantees that diffs can be applied unambiguously, even if the same line of code appears multiple times.
*   **File Name:** Included to match the format of the base model's (DeepSeek-Coder) pre-training data.
*   **No Vocabulary Modification:** The team decided against adding the sentinel tokens as special tokens to the model's vocabulary. The model performed well with each sentinel being mapped to 3-5 existing tokens, and the marginal improvement to decoding latency was not deemed necessary.

### 11. Measuring results

#### 11.1. Offline evaluation methodology

*   The finetuned model was evaluated against baselines on the `Leetcode Repair Eval` and `Replit Repair Eval`.
*   For few-shot evaluations of baseline models, examples were chosen randomly from the training set by matching the error code of the sample being evaluated.
*   Inference was performed with `temperature=0.1`, `top_p=0.95`, and `top_k=50`.
*   **Results on Leetcode Repair Eval:** `Replit Code Repair 7B` (89.44% functional correctness) was competitive with GPT-4 Turbo (89.16%) and Claude-3-Opus (88.61%), and significantly outperformed its base model (66.94%). (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_033/img_007.png`)
*   **Results on Replit Repair Eval:** `Replit Code Repair 7B` (74.55% AST match string fallback) was competitive with GPT-4 Turbo (72.23%) and significantly outperformed all other models, including Claude-3-Opus (65.81%) and its base model (41.31%). (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_033/img_008.png`)
*   **Scaling Experiments:**
    *   **Data Scaling:** Performance on the Leetcode eval improved consistently as the finetuning dataset size was increased from 10k to 75k samples.
    *   **Model Scaling:** Performance on both evals improved as model size was increased from 1.3B to 33B parameters (using the DeepSeek-Coder v1 family).

#### 11.2. A/B test design

[NO INFO] The article mentions plans to collect user interaction data (accepted/rejected fixes) once the model is in production, which would enable A/B testing and online