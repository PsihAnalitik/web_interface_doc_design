**Company**: Airbnb
**Title**: How AI Text Generation Models Are Reshaping Customer Support at Airbnb
**Technology area**: Generative AI & LLM
**Source URL**: https://medium.com/airbnb-engineering/how-ai-text-generation-models-are-reshaping-customer-support-at-airbnb-a851db0b4fa3
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The system is designed to improve Airbnb's community support (CS) products by leveraging AI text generation models. The goal is to build more effective and scalable solutions for assisting both customers (guests and hosts) and human support agents. The core problem is that large-scale customer support applications face challenges with long-tail corner cases, scalability, and the high cost of labeling training data.

This document covers three specific use cases where generative models were applied:
1.  **Content Recommendation**: Powering Help Center search and a Helpbot to provide users with relevant support articles.
2.  **Real-time Agent Assistance**: Providing "just-in-time" guidance and suggested response templates to human support agents during conversations with users.
3.  **Chatbot Paraphrasing**: Improving chatbot interactions by having the bot rephrase the user's problem to confirm understanding and build user confidence.

#### 1.2. Relevance & reasons

Traditional discriminative NLP models (classifiers) were found to be restrictive for CS applications. The key reasons for adopting generative models are:
*   **Knowledge Encoding**: Generative models can encode domain knowledge from large-scale pre-training on Airbnb's historical support data. This allows the model to generate answers based on encoded human knowledge, leading to better performance than traditional classification.
*   **Scalability and Cost**: The "unsupervised" nature of these models reduces the dependency on costly, large-scale manual data labeling. This helps overcome the challenge of designing comprehensive label taxonomies for the long-tail distribution of user issues.
*   **Unified Problem Formulation**: Text generation can frame various ML tasks (classification, ranking) as a single language modeling problem, which is considered more natural and less restrictive. This is achieved through "prompting".

#### 1.3. Expectations

The primary expectation is to improve the user experience and operational efficiency of the customer support ecosystem.
*   **For customers**: Provide more relevant help content and have more effective chatbot interactions.
*   **For support agents**: Receive accurate, contextual, and policy-compliant suggestions to resolve user issues more efficiently and consistently.
*   **For the chatbot**: Increase user engagement by demonstrating a correct understanding of the user's problem.

#### 1.4. Previous work

*   **Content Recommendation**: The previous system used a pointwise ranker based on a discriminative classification model, **XLMRoBERTa**.
*   **Real-time Agent Assistance**: The prior system for gating suggestion templates relied on a combination of API checks and separate model-based intent checks.
*   **Chatbot Paraphrasing**: The chatbot existed previously but lacked the paraphrasing capability, which led to lower user engagement.

#### 1.5. Usage volumes and patterns

*   The Content Recommendation model is integrated into Airbnb's Help Center, which serves **millions of active users**.
*   The Real-time Agent Assistant is used by Airbnb's **Community Support (CS) ambassadors**.
*   The system leverages "massive amounts" and "many years" of historical agent-user communication data for training.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Overall**: Build more effective, scalable, and innovative AI products for customer support. Improve user experience and key business metrics.
*   **Content Recommendation**: Significantly improve the relevance of recommended support documents compared to the classification-based baseline.
*   **Real-time Agent Assistance**: Increase the engagement rate of agents with the suggested templates. Help agents resolve user issues more efficiently and consistently.
*   **Chatbot Paraphrasing**: Significantly improve the chatbot's user engagement rate. Give users confidence that the bot understands their problem correctly.

#### 2.2. Anti-goals

*   **Avoid Restrictive Formulations**: Move away from traditional classification paradigms that are seen as "unnatural, counterproductive, and restrictive".
*   **Avoid Generic Outputs**: The system should not generate "bland, generic, uninformative replies". For example, a paraphrase like "I understand that you have some issues with your reservation" is considered unhelpful and should be avoided.

### 3. Risks and constraints

#### 3.1. Technical risks and constraints

*   **Model Quality**: Generative models have a tendency to produce generic and uninformative text, which was a major challenge for the paraphrase model.
*   **Training Time**: Training large generative models is computationally expensive and slow. Initial training took "weeks" before being optimized.
*   **Hyperparameter Tuning**: Tuning large models is difficult. The team mitigates this by first running experiments on smaller datasets to find a good direction for parameter settings.

#### 3.2. Data constraints

*   **Labeling Cost and Scalability**: Manually labeling data at the scale of Airbnb's CS operations is prohibitively expensive and does not scale to cover the long-tail of user intents.
*   **Data Quality**: The training data can be noisy.
    *   For the agent assistant, logging-based data has low precision and random noise, while annotation-based data has low coverage.
    *   For the paraphrase model, the heuristically-mined training data contained a large volume of generic replies, which biased the model's output.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Content Recommendation**: The generative model demonstrated "significant improvements in the key performance metric for support document ranking". The specific metric (e.g., NDCG, MRR) is not named.
*   **Paraphrase Model**: Model quality was evaluated qualitatively by analyzing the genericity of the output. A quantitative offline metric is not mentioned.

#### 4.2. Online/business metrics

*   **Content Recommendation**: A/B testing showed "significant business metric improvement" and confirmed that the model recommends documents with "significantly higher relevance".
*   **Real-time Agent Assistance**: Online testing with CS ambassadors showed a "large engagement rate improvement".
*   **Chatbot Paraphrasing**: The feature "significantly improved our bot’s engagement rate" in production.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **General**: The primary data source is "massive amounts of records of our human agents offering help to our guests and hosts at Airbnb," collected over "many years".
*   **Content Recommendation**:
    *   **Inputs**: User's issue description, candidate document text (title, summary, keywords), and textual representations of user and reservation information for personalization.
    *   **Labels**: Derived from production traffic data. [inferred] Labels are likely based on implicit user feedback like clicks on recommended articles.
*   **Real-time Agent Assistance**:
    *   **Inputs**: Concatenated multi-round user-agent conversations (chat history).
    *   **Training Data**: A combination of two sources:
        1.  **Annotation-based data**: High precision, low coverage, consistent noise.
        2.  **Logging-based data**: Low precision, high case coverage, random noise.
*   **Chatbot Paraphrasing**:
    *   **Source**: User-agent conversations.
    *   **Labels**: Generated via a heuristic. If an agent's reply starts with the phrase "I understand that you…", the preceding user message is used as the source text and the agent's reply is the target paraphrase. This method yielded **millions of training labels**.

#### 5.2. Data quality and cleaning

*   **Real-time Agent Assistance**: The best model performance was achieved by combining the high-precision annotation dataset with the high-coverage logging dataset, balancing their respective strengths and weaknesses.
*   **Chatbot Paraphrasing**: The initial training data was heavily skewed towards generic replies. To fix this, the team performed the following steps:
    1.  Ran text clustering on the target (paraphrase) data using pre-trained **Sentence-Transformers** models.
    2.  Manually labeled clusters that were "too generic".
    3.  Used **Sentence-Transformers** to filter out these generic examples from the final training dataset. This approach "worked significantly better" than other methods.

### 6. Validation schema

*   **Content Recommendation**: The model was evaluated using "production traffic data sampled from the same distribution as the training data." This implies a standard train/test split based on production logs.
*   **Other Use Cases**: [NO INFO]

### 7. Baseline solution

*   **Content Recommendation**: A pointwise ranker implemented using **XLMRoBERTa**, a classification-based model. The generative model was compared directly against this baseline.
*   **Real-time Agent Assistance**: The previous system used a combination of API checks and separate model intent checks to gate suggestions, which was less sophisticated than the unified QA model approach.
*   **Chatbot Paraphrasing**: The baseline was the existing chatbot without the paraphrasing feature.

### 8. Errors and their analysis

The primary error analyzed in the source is for the **Paraphrase Model**.

*   **Error Type**: The model tended to generate "bland, generic, uninformative replies" for many different inputs (e.g., "I understand that you have some issues with your reservation.").
*   **Root Cause Analysis**: The team discovered the issue was in the training data itself. They ran text clustering on the target paraphrases and found that the dataset contained an excessive number of generic replies, which the model learned to replicate.
*   **Alternative Solutions Explored**:
    1.  **Reranking**: Building a backward model to predict `P(Source|target)` and use it to rerank and filter generic outputs.
    2.  **Filtering**: Using rule-based or other model-based filters on the generated output.
*   **Final Solution**: The most effective solution was to clean the training data by identifying and filtering out the generic examples using text clustering and Sentence-Transformers.

### 9. Training pipelines

#### 9.1. Tooling

*   **Model Backbones**: MT5 (for content recommendation), T5-base, Narrativa, BART, PEGASUS, GPT2. T5 was found to perform best for the paraphrase task.
*   **Training Acceleration**: **DeepSpeed** library was used for distributed training on multi-GPU cores, reducing training time from "weeks to days".
*   **Data Processing**: **Sentence-Transformers** library was used for similarity modeling to cluster and filter the paraphrase training data.

#### 9.2. Training process

*   The overall paradigm is large-scale pre-training on Airbnb's domain-specific data, followed by fine-tuning on task-specific data.
*   **Prompt Engineering**: A key part of the process is designing high-quality prompts to instruct the model on the task. Prompts are combined with natural language annotations (hints) to contextualize the input.
*   **Hyperparameter Tuning**: Due to the long training cycles, experiments are first conducted on smaller datasets to get a better direction on parameter settings before scaling up.
*   **Dataset Composition**: For the agent assistant model, experiments were run on various compositions of annotation-based and logging-based data, with the combination of the two yielding the best results.

### 10. Features

The system moves away from traditional feature engineering towards a paradigm of "knowledge encoding" and "prompt design". The "features" are constructed as formatted text inputs.

#### 10.1. Content Recommendation Model Input

The input is a single text string composed of:
*   **Prompt**: A textual instruction informing the model that a binary answer ("Yes" or "No") is expected.
*   **Annotations**: Hints that clarify the role of different parts of the input text.
*   **Issue Description**: The user's query.
*   **Document Representation**: Text from the candidate document, including its title, summary, and keywords.
*   **Personalization**: Textual representations of the user and their reservation information.

#### 10.2. Real-time Agent Assistant Model Input

*   **Input Text**: Multiple rounds of user-agent conversations concatenated together to provide chat history as context.
*   **Prompt**: A specific question that captures the user intent to be checked (e.g., "Is this user canceling due to a COVID sickness?"). Different prompts can be used at serving time to elicit different pieces of information from the same conversation history.

#### 10.3. Paraphrase Model Input

*   **Input Text**: The user's problem description.
*   **Target Text (for training)**: The agent's paraphrased version of the problem.

### 11. Measuring results

#### 11.1. Offline evaluation

*   **Content Recommendation**: The MT5-based generative classifier was evaluated on a test set sampled from production traffic and showed "significant improvements" on a key ranking metric compared to the XLMRoBERTa baseline.

#### 11.2. A/B testing

*   **Content Recommendation**: An online A/B experiment was run in the Airbnb Help Center. The results confirmed the offline findings, showing the generative model recommended documents with "significantly higher relevance".
*   **Real-time Agent Assistance**: The QA model was evaluated via "online testing with real CS ambassadors," which demonstrated a "large engagement rate improvement."
*   **Chatbot Paraphrasing**: The feature was launched to production, where it "significantly improved our bot’s engagement rate."

### 12. Integration and Serving

#### 12.1. API design and serving pattern

*   **Content Recommendation**: The model serves as a pointwise ranker. It computes a relevance score for a (user issue, document) pair. This powers both the **Help Center search** and the **Helpbot's content recommendation**.
*   **Real-time Agent Assistance**: The model provides "just-in-time guidance" to agents. At serving time, it takes the conversation history and a specific prompt as input. The model's answer is used to gate which suggestion templates are displayed to the agent.
*   **Chatbot Paraphrasing**: The model is integrated into the AI chatbot flow. It takes the user's initial message, generates a paraphrase, and the bot presents this paraphrase back to the user to confirm understanding before proceeding.

#### 12.2. Infrastructure

*   **Training**: Multi-GPU core infrastructure is used, managed with the **DeepSpeed** library.

#### 12.3. SLAs, latency, and fallback

[NO INFO]

### 13. Monitoring

[NO INFO]

### 14. Operations

[NO INFO]