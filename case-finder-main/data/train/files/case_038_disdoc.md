**Company**: Booking
**Title**: Building a GenAI Agent for Partner-Guest Messaging
**Technology area**: AI agents
**Source URL**: https://booking.ai/building-a-genai-agent-for-partner-guest-messaging-f54afb72e6cf
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The system addresses the communication channel between accommodation partners and guests on Booking.com's messaging platform. Guests frequently contact partners with questions regarding check-in times, parking, special requests, and other logistics. Partners typically reply to these messages manually.

#### 1.2. Relevance & reasons

Manual responses can be slow, especially during busy periods, leading to delays for travelers seeking information. This can cause anxiety for guests and, in some cases, lead to cancellations and lost revenue for partners. The goal is to create a Generative AI (GenAI) agent to assist partners by automatically suggesting relevant responses to guest inquiries, thereby saving time and improving response speed and accuracy.

#### 1.3. Expectations

The system is expected to assist partners by suggesting a relevant response to each guest inquiry. The response can be either an existing partner-created template or a custom-generated free-text answer. Key product expectations include:
- **Accuracy and Safety**: The system must avoid providing outdated or incorrect information.
- **Controlled Automation**: Certain sensitive topics (e.g., refund requests) should never be answered automatically. A human-in-the-loop approach is required to maintain trust.
- **Performance**: The solution must be fast, scalable, and cost-efficient.

#### 1.4. Previous work

Before the GenAI agent, Booking.com provided "response templates for common questions." However, this solution still required partners to manually search for and select the appropriate template for each message.

#### 1.5. Usage volumes and patterns

- The agent helps manage "tens of thousands of guest messages every day."
- This is a subset of the total volume of "about 250,000 daily partner-guest exchanges."

### 2. Goals and anti-goals

#### 2.1. Goals

- **Primary Goal**: Assist partners by automatically suggesting relevant and accurate responses to guest inquiries.
- **Efficiency**: Save partners' time, reduce time spent on repetitive questions, and speed up response times.
- **Quality**: Improve the accuracy and consistency of partner-guest communication.
- **Business Impact**: Reduce follow-up messages and improve user satisfaction (a 70% boost was observed in pilots).
- **Technical**: The system must be fast, scalable, and cost-efficient.
- **Strategic**: Lay the groundwork for future, more advanced automation in partner-guest communication.

#### 2.2. Anti-goals

- The system should **not** be fully autonomous. It operates with a human-in-the-loop to ensure trust and reliability.
- The system should **not** answer questions on restricted topics, such as refund requests.
- The system should **not** provide outdated or incorrect information.
- The goal is **not** just to generate faster replies, but to produce communication that feels natural and aligns with each partner's unique voice and style.

### 3. Risks and constraints

- **Data Quality**: The system must handle inconsistent data quality across different properties and gaps in response template coverage.
- **Multilingual Support**: The solution needs to function effectively across many languages.
- **Cost and Latency**: Complex, multi-step agentic systems can become expensive in terms of both compute cost and latency. Efficiency must be a primary design consideration.
- **Safety and Accuracy**: There is a critical risk of providing incorrect or outdated information to guests. The system must have robust guardrails.
- **Dependencies**: The system depends on OpenAI's GPT-4 Mini model, accessed via an internal LLM gateway, and internal backend systems for property and reservation data.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

- **Retrieval Quality**: `recall@k` was used to evaluate and benchmark embedding models for the response template retrieval tool. MiniLM was chosen for its strong performance on real-world data.
- **Response Quality (Manual)**: Manual annotation of AI-generated answers was performed using the SuperAnnotate platform to review quality and conduct error analysis.
- **Response Quality (Automated)**: An "LLM-as-a-Judge" was implemented to enable scaled evaluation of different agent architectures, LLMs, and prompt modifications.

#### 4.2. Online/business metrics

- **User Satisfaction**: Measured via live pilots, showing a 70% increase.
- **Response Time**: The agent suggests or sends replies "within minutes" for supported topics.
- **Follow-up Message Rate**: A reduction in follow-up messages was a key success metric.
- **User Feedback**: In-tool user feedback is collected to validate performance in production.
- **Adoption**: The system handles tens of thousands of messages daily.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

- **Guest Messages**: The primary input to the agent.
- **Partner Response Templates**: Predefined responses created by partners, used as the preferred response type.
- **Historical Partner Replies**: Real free-text replies from partners used to build the evaluation dataset.
- **Property Details**: Contextual information about the accommodation, retrieved via a dedicated tool.
- **Reservation Details**: Contextual information about a specific booking (e.g., room type, dates, number of travelers), retrieved via a dedicated tool.

#### 5.2. Labeling strategy

An evaluation dataset was constructed using representative guest messages paired with real partner replies (both template-based and free-text) and associated contextual data (property and reservation details). This dataset was used for manual annotation on the SuperAnnotate platform to assess the quality of AI-generated responses.

#### 5.3. Data quality and cleaning

- **PII Redaction**: The agent applies a guardrail mechanism to redact personally identifiable information (PII) from incoming messages before processing.
- **Template Freshness**: Partner-created response templates are streamed in real-time via Kafka to the Weaviate vector database, ensuring the retrieval index is always up-to-date.

#### 5.4. ETL

Template updates are streamed via Kafka to continuously update the embeddings stored in the Weaviate vector database.

### 6. Validation schema

#### 6.1. Train/validation/test split

A representative dataset of guest messages, real partner replies, and contextual data was created for testing and evaluation. This dataset was used to benchmark embedding models and evaluate agent architectures. The article does not specify the exact split methodology (e.g., time-based, random).

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets

[NO INFO]

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

The baseline was the existing manual workflow where partners used the Booking.com messaging platform to reply to guests. This included a feature that provided "response templates for common questions," but partners still had to manually search for and select the correct one. The GenAI agent is designed to automate this selection and generation process.

### 8. Errors and their analysis

#### 8.1. Error taxonomy

Error analysis was conducted on manually annotated responses, which identified recurring issues such as:
- **Missing Context**: The agent generated a response without sufficient information.
- **Overly Generic Phrasing**: The generated response lacked specificity or personalization.

#### 8.2. Diagnostic approaches

- **"No Response" Action**: The agent is designed to explicitly refrain from answering when it lacks the necessary information or when a query falls into a restricted "do not answer" category (e.g., refund requests). This serves as a primary fallback.
- **Guardrails**: The agent first checks if a message topic belongs to a "do not answer" category.
- **Live Monitoring**: The Arize platform is used to inspect sampled traces from production, allowing for early identification of potential issues.

### 9. Training pipelines

#### 9.1. Tooling

- **Programming Language**: Python
- **Agent Framework**: LangGraph
- **LLM**: OpenAI's GPT-4 Mini
- **Web Framework**: FastAPI
- **Deployment**: Kubernetes microservice
- **Vector Database**: Weaviate
- **Embedding Models**:
    - MiniLM (default, for English)
    - E5-Small (for non-English cases)
- **Data Streaming**: Kafka
- **Annotation Platform**: SuperAnnotate
- **AI Observability**: Arize
- **Backend Access**: GraphQL for querying property and reservation details.

#### 9.2. Automation

An end-to-end evaluation pipeline powered by an automated LLM-as-a-Judge was built to enable rapid iteration on agent architectures, LLMs, and prompts while maintaining high performance standards.

#### 9.3. CI/CD

[NO INFO]

### 10. Features

The agent uses a tool-calling architecture where an LLM selects which tools to run based on the query. These tools provide the necessary context (features) for generating a response.

#### 10.1. Feature categories (Tools)

- **Response Template Retrieval Tool**:
    - Embeds the guest message into a vector space.
    - Performs a k-nearest-neighbors search (k=8) in Weaviate to find semantically similar partner-created response templates.
    - Filters out weak matches using a similarity threshold.
- **Property Details Tool**: Translates the agent's request into a GraphQL query to retrieve specific information about the partner's property from backend systems.
- **Reservation Details Tool**: Provides reservation-specific data such as room type, check-in/check-out dates, and number of travelers via GraphQL queries.

#### 10.2. Feature computation

- **Template Embeddings**: Stored and indexed in Weaviate. The index is updated in real-time via Kafka as partners modify their templates.
- **Property/Reservation Details**: Fetched on-demand at inference time by executing GraphQL queries against backend systems.

#### 10.3. Feature selection

The agent's core LLM (GPT-4 Mini) reasons about the guest query and available context to pre-select which tools to run concurrently. This avoids unnecessary tool calls, making the system more efficient in terms of token usage and cost.

### 11. Measuring results

#### 11.1. Offline evaluation

- A structured, data-driven evaluation process was followed.
- A representative dataset of real-world communications was used for testing.
- Multiple rounds of manual annotation were conducted using SuperAnnotate.
- An LLM-as-a-Judge was used to scale evaluation across development cycles.
- Embedding models were benchmarked for retrieval quality (`recall@k`).

#### 11.2. A/B test design

- **Hypothesis**: Automating response suggestions will improve partner efficiency and user satisfaction.
- **Methodology**: "Live pilots" and "controlled experiments" were used to validate model performance in production.
- **Primary Metrics**: User satisfaction, reduction in follow-up messages, and response time.
- **Results**: The pilots demonstrated a 70% boost in user satisfaction.

#### 11.3. Reporting

The Arize AI observability platform is used for live monitoring, allowing teams to inspect sampled traces and monitor agent behavior in production.

### 12. Integration and Serving

#### 12.1. API design

The agent operates as a microservice within the Booking.com ecosystem. It exposes an interface that accepts a guest inquiry and context, and its logic determines one of three actions:
1.  **Template Response**: Suggest a predefined template.
2.  **Custom Response**: Suggest a generated free-text reply.
3.  **No Response**: Defer to the human partner.

#### 12.2. Infrastructure

- **Compute**: The agent runs as a microservice in a Kubernetes environment.
- **Web Framework**: FastAPI.
- **LLM Gateway**: All calls to OpenAI's GPT-4 Mini are routed through an internal LLM gateway that provides additional safety layers like prompt-injection detection.
- **Tool Hosting**: The agent's tools are hosted on a central MCP server, also running on Kubernetes.
- **Vector Search**: Weaviate is used as the vector database for template retrieval.

#### 12.3. SLAs, latency, and fallback

- **Latency**: The agent can suggest or send a reply "within minutes" for supported topics. Latency is a key consideration, as complex agentic reasoning can be slow.
- **Fallback Strategy**: The primary fallback is the "No Response" action. If the agent has low confidence, lacks necessary information, or the topic is out of scope, it refrains from answering, and the message is handled manually by the partner. This maintains a human-in-the-loop.

### 13. Monitoring

- **Data Quality**: PII is redacted from incoming messages as a guardrail. [NO INFO] on further data quality monitoring.
- **Model Quality**:
    - **AI Observability**: Arize is used to inspect sampled traces, monitor agent behavior, and identify potential issues early.
    - **User Feedback**: In-tool user feedback is collected to validate production performance.
- **Input/target drift**: [NO INFO]
- **Engineering Metrics**: Latency and compute cost are cited as critical metrics that are monitored from the start of development.
- **Alerting**: [NO INFO]

### 14. Operations

- **Retraining Cadence**: The response template index is updated in real-time via Kafka streams. The cadence for updating the core agent logic or embedding models is described as a "continuous feedback loop" guided by evaluation cycles.
- **Incident Response and Rollback**: The "human-in-the-loop" design is the core safety mechanism. If the agent fails or is unconfident, the system gracefully falls back to the manual workflow where the partner handles the message.
- **Stakeholder Interaction**: The system is designed to assist partners, who are the direct users of the suggested responses. Future work aims to personalize the agent's tone and style to better match each partner's voice.