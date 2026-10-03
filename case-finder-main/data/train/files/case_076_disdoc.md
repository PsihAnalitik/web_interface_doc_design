**Company**: Meta
**Title**: Introducing Code Llama, a state-of-the-art large language model for coding
**Technology area**: Generative AI & LLM
**Source URL**: https://ai.meta.com/blog/code-llama-large-language-model-coding/
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The project's goal is to create a state-of-the-art large language model (LLM) specialized for coding tasks. The model, named Code Llama, is designed to assist developers, make their workflows more efficient, and lower the barrier to entry for people learning to code. It can be used as a productivity and educational tool.

The system takes text prompts, which can be natural language instructions or existing code snippets, and generates code or natural language about code in response.

#### 1.2. Relevance & reasons

Programmers are increasingly using LLMs to assist with a variety of tasks, from writing new software to debugging existing code. The primary goal is to improve developer efficiency, allowing them to focus on human-centric aspects of their job rather than repetitive tasks. By releasing a publicly available, code-specific model, Meta aims to facilitate the development of new technologies and leverage the community to evaluate capabilities, identify issues, and fix vulnerabilities.

#### 1.3. Expectations

The model is expected to handle several key use cases:
*   **Code Generation**: Generating code from natural language prompts (e.g., “Write me a function that outputs the fibonacci sequence.”).
*   **Code Completion**: Completing partially written code. The 7B and 13B models support this "out of the box" via fill-in-the-middle (FIM) training.
*   **Debugging**: Assisting developers in debugging scenarios, especially in large codebases where it can be challenging to track all relevant code. The model's large context window allows passing entire files for analysis.
*   **Code Documentation**: Generating natural language about code.

The model supports many popular programming languages, including Python, C++, Java, PHP, Typescript (Javascript), C#, and Bash.

#### 1.4. Previous work

Code Llama is a code-specialized version of Llama 2. It was created by further training Llama 2 on code-specific datasets. It is benchmarked against its predecessor, Llama 2, as well as other open-source and proprietary models like StarCoder, Codex, and ChatGPT.

#### 1.5. Usage volumes and patterns

The system is designed to serve different requirements through various model sizes:
*   **7B and 13B models**: Faster and suitable for low-latency tasks like real-time code completion. The 7B model can be served on a single GPU.
*   **34B and 70B models**: Return the best results and allow for better coding assistance, but are more resource-intensive.

The models support a context window of up to 100,000 tokens, enabling use cases that require large amounts of context, such as analyzing an entire codebase for relevant generation or debugging.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Improve Developer Productivity**: Make developer workflows faster and more efficient.
*   **Enhance Education**: Lower the barrier to entry for people learning to code and serve as an educational tool.
*   **State-of-the-Art Performance**: Achieve performance better than existing open-source, code-specific LLMs.
*   **Support Multiple Languages**: Be proficient in popular programming languages like Python, C++, Java, etc.
*   **Enable New Use Cases**: The large context window (up to 100k tokens) is intended to unlock new applications, such as whole-codebase analysis.
*   **Promote Open Innovation and Safety**: Release the model publicly to allow the community to evaluate capabilities, identify issues, fix vulnerabilities, and build new tools.

#### 2.2. Anti-goals

*   **Not for General Natural Language Tasks**: The base Code Llama and Code Llama - Python models are not designed to follow general natural language instructions and are not appropriate as foundation models for non-coding tasks. The `Code Llama - Instruct` variant is recommended for conversational code generation.

### 3. Risks and constraints

#### 3.1. Risks

*   **Generation of Malicious Code**: A primary risk is the model's potential to generate malicious code like computer viruses.
    *   **Mitigation**: Meta conducted quantitative red teaming efforts, creating prompts to solicit malicious code. The results showed that Code Llama provided safer responses compared to GPT-3.5 Turbo. The research paper provides more details on red teaming by experts in responsible AI, offensive security, and malware development.

#### 3.2. Constraints

*   **Licensing**: Users must abide by the community license provided, which is the same as Llama 2's license.
*   **Acceptable Use Policy**: Usage must conform to Meta's acceptable use policy.
*   **Specialization**: The base model is specialized for code and is not suitable for general-purpose NLP tasks.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

The model's performance was evaluated on two popular coding benchmarks:
*   **HumanEval**: Tests the model's ability to complete code based on docstrings (pass@1).
*   **Mostly Basic Python Programming (MBPP)**: Tests the model's ability to write code based on a description (pass@1).

Benchmark results for key models (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_076/img_006.png`):
*   **Code Llama 34B**:
    *   HumanEval: 48.8%
    *   MBPP: 55.0%
*   **Code Llama - Python 34B**:
    *   HumanEval: 53.7%
    *   MBPP: 56.2%
*   **Code Llama - Instruct 70B**:
    *   HumanEval: 67.8%
    *   MBPP: 62.2%
*   **Llama 2 70B (Baseline)**:
    *   HumanEval: 30.5%
    *   MBPP: 45.4%
*   **ChatGPT (GPT-3.5)**:
    *   HumanEval: 48.1%
    *   MBPP: 52.2%

A safety evaluation was also performed by creating prompts to solicit malicious code and scoring the model's responses against a baseline (GPT-3.5 Turbo).

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

Code Llama is built upon the Llama 2 foundation models. It was created by further training Llama 2 on code-specific datasets.
*   **Base Training**: The 7B, 13B, and 34B models were trained on **500B tokens** of code and code-related data. The 70B model was trained on **1T tokens**.
*   **Python Specialization**: The `Code Llama - Python` variant was further fine-tuned on **100B tokens** of Python code.
*   **Instruction Tuning**: The `Code Llama - Instruct` variant was fine-tuned on a dataset of natural language instructions and their expected outputs. This involved **5B tokens** of data. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_076/img_005.png`)
*   **Long Context Fine-tuning**: The models were fine-tuned to handle long contexts (up to 100,000 tokens). This stage used **20B tokens**. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_076/img_005.png`)

#### 5.2. Labeling strategy

For instruction tuning, the model was fed a dataset where each instance consists of a "natural language instruction" input and the expected output. This makes the model better at understanding human prompts.

#### 5.3. Data quality issues and cleaning

[NO INFO]

### 6. Validation schema

#### 6.1. Train/validation/test split strategy

[NO INFO]

#### 6.2. Validation approach

*   **Performance Evaluation**: The models were evaluated against standard academic benchmarks for code, including HumanEval and MBPP.
*   **Safety Evaluation**: A red teaming exercise was conducted to assess the risk of generating malicious code. This involved creating adversarial prompts with clear intent to solicit harmful code and comparing Code Llama's responses to those of GPT-3.5 Turbo.
*   **Community Evaluation**: By releasing the model publicly, Meta encourages the entire community to evaluate its capabilities, identify issues, and fix vulnerabilities. The Responsible Use Guide recommends that downstream developers perform safety studies on code-specific use cases (e.g., generating malware) and leverage safety datasets for evaluation.

### 7. Baseline solution

The performance of Code Llama was compared against several other models, which serve as baselines:
*   **Foundation Model**: Llama 2 (the model Code Llama is based on).
*   **Open-Source Models**: StarCoder.
*   **Proprietary Models**: Codex, GPT-3.5, and GPT-4 (reported results).

Code Llama 34B scored 53.7% on HumanEval and 56.2% on MBPP, outperforming other state-of-the-art open solutions at the time of release and performing on par with ChatGPT.

### 8. Errors and their analysis

The primary error type discussed is the generation of unsafe or malicious code.
*   **Analysis**: A quantitative evaluation was performed as part of red teaming efforts to measure the model's propensity to generate malicious code in response to adversarial prompts.
*   **Mitigation**: The model was found to produce safer responses compared to GPT-3.5 Turbo. The Responsible Use Guide provides further guidance for downstream developers on evaluating and mitigating such risks, including using code-specific evaluation benchmarks and safety datasets.

### 9. Training pipelines

The training process for Code Llama involves several stages of continued training and fine-tuning starting from the Llama 2 foundation models. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_076/img_005.png`)

1.  **Foundation Model**: Start with pre-trained Llama 2 models (7B, 13B, 34B, 70B).
2.  **Code Pre-training**: Further train the models on a large corpus of code and code-related data (500B tokens for 7B/13B/34B, 1T tokens for 70B). This creates the base `Code Llama` models.
    *   **Fill-in-the-Middle (FIM)**: The 7B and 13B models are also trained with a FIM objective to support code completion tasks.
3.  **Specialization Fine-tuning (Parallel Tracks)**:
    *   **Python Specialization**: The base `Code Llama` models are further fine-tuned on 100B tokens of Python code to create `Code Llama - Python`.
    *   **Instruction Fine-tuning**: The base `Code Llama` models are fine-tuned on 5B tokens of instruction-output pairs to create `Code Llama - Instruct`. This makes the model better at following human instructions.
4.  **Long Context Fine-tuning**: All models are trained on sequences of 16,000 tokens and show improvements on inputs up to 100,000 tokens. This capability is refined via a specific long-context fine-tuning stage using 20B tokens.

**Tooling**:
*   The AI community's use of **Python** and **PyTorch** is highlighted as important.
*   Training recipes are made available on Meta's **GitHub repository**.

### 10. Features

The primary "feature" is the input prompt provided by the user. This can consist of:
*   **Natural Language**: Instructions describing the desired code.
*   **Code**: Existing code snippets for completion, debugging, or explanation.
*   **Combined Input**: A mix of code and natural language.

**Feature Characteristics**:
*   **Context Length**: The models are trained on sequences of 16,000 tokens and can handle inputs with up to 100,000 tokens of context. This allows users to provide large amounts of context from their codebase to make generations more relevant or to debug large files.
*   **Supported Languages**: The model is proficient in Python, C++, Java, PHP, Typescript (Javascript), C#, and Bash.

### 11. Measuring results

#### 11.1. Offline evaluation

Offline evaluation was conducted using standard coding benchmarks to compare Code Llama against other models. The primary metrics were pass@1 on HumanEval and MBPP. The results demonstrated that Code Llama variants outperformed other open-source models and were competitive with closed-source models like ChatGPT. For example, Code Llama 34B scored 53.7% on HumanEval, compared to 30.5% for Llama 2 70B and 48.1% for ChatGPT.

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting

Results are published in the official blog post and the accompanying research paper. The reporting format consists of tables comparing the performance scores of different Code Llama variants and sizes against baseline models on the chosen benchmarks. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_076/img_006.png`)

### 12. Integration and Serving

#### 12.1. API design

The model interacts via a text-prompt interface.
*   It can accept natural language instructions, code snippets, or a combination.
*   It outputs generated code or natural language about code.
*   The 7B and 13B models also support a fill-in-the-middle (FIM) capability, which is suitable for code completion integrations.

#### 12.2. Infrastructure

Different model sizes are provided to cater to different serving and latency needs:
*   **7B model**: Can be served on a single GPU, making it suitable for low-latency, real-time applications.
*   **13B model**: Also designed to be faster and more suitable for low-latency tasks.
*   **34B and 70B models**: Offer the best performance and coding assistance but require more substantial computational resources, leading to higher latency.

#### 12.3. SLAs, latency budgets, and fallback strategies

The choice of model size (7B/13B vs. 34B/70B) represents a direct trade-off between performance (quality of assistance) and latency. Smaller models are explicitly recommended for tasks requiring low latency.

#### 12.4. Release cycle

The model weights are released publicly for download. The initial release included 7B, 13B, and 34B parameter models, with the 70B model released later.

### 13. Monitoring

The provided source material focuses on guidance for downstream developers rather than Meta's internal monitoring practices. The **Responsible Use Guide** recommends that developers building on Code Llama should:
*   Evaluate their models using code-specific benchmarks.
*   Perform safety studies on use cases like generating malware or viruses.
*   Leverage safety datasets for automatic and human evaluations.
*   Conduct red teaming on adversarial prompts.

### 14. Operations

#### 14.1. Retraining cadence

[NO INFO]

#### 14.2. Ownership

Meta has released the model, training recipes, and a Responsible Use Guide to the public. The open approach implies a degree of community involvement in identifying issues and vulnerabilities.

#### 14.3. Incident response and rollback procedures

The open-source nature of the release is presented as a mechanism for improving safety. By releasing the model, the community can help "evaluate their capabilities, identify issues, and fix vulnerabilities." No specific internal incident response plan is detailed in the article.