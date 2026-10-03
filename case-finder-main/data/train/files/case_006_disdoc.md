**Company**: Slack
**Title**: How we built enterprise search to be secure and private
**Technology area**: RAG
**Source URL**: https://slack.engineering/how-we-built-enterprise-search-to-be-secure-and-private/
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The project's origin is an extension of Slack's core identity as a "Searchable Log of all Communication and Knowledge". The goal is to evolve Slack from a searchable log of its own content into an intelligent, unified search platform that also includes knowledge from key external applications. This feature is part of the broader Slack AI initiative.

#### 1.2. Relevance & reasons

Users' knowledge and work are often fragmented across multiple tools. By integrating external sources into Slack search, users can surface up-to-date, relevant, and permissioned content directly within their primary communication hub. This creates a more powerful and efficient search experience, pulling context from across key tools to satisfy user queries and save time. The initial external sources are Google Drive and GitHub, with plans to add more.

#### 1.3. Expectations

The system is expected to provide a search experience that is:
*   **Secure and Private**: Adhering to enterprise-grade compliance and security standards.
*   **Permission-aware**: Only surfacing content that the user is already authorized to access in both Slack and the external systems.
*   **Up-to-date**: Search results from external sources must reflect the current state and permissions in the source system, avoiding stale data.
*   **Seamless**: The integration should feel like a natural extension of the existing Slack search and Slack AI capabilities.

#### 1.4. Previous work

This enterprise search system is built on top of the existing Slack AI platform. It reuses many of the same architectural patterns and principles, including:
*   Using closed-source LLMs hosted in an escrow VPC on AWS.
*   Employing Retrieval Augmented Generation (RAG) to provide context to the LLM.
*   Leveraging existing compliance infrastructure (e.g., Encryption Key Management, International Data Residency).

#### 1.5. Usage volumes and patterns

[NO INFO]

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Unified Search**: Integrate external knowledge sources (starting with Google Drive and GitHub) into Slack's search and AI Answers.
*   **Maintain Security Boundary**: Ensure customer data, whether from Slack or external sources, never leaves Slack's trust boundary.
*   **Real-time Data and Permissions**: Guarantee that all data and permissions from external sources are fetched in real-time and are always up-to-date.
*   **Explicit User Control**: Require explicit opt-in from both organization administrators and individual users before accessing any external data. Users and admins must be able to revoke access at any time.
*   **Adherence to Least Privilege**: Only request the minimum necessary permissions (read-only OAuth scopes) to satisfy search queries.

#### 2.2. Anti-goals

*   **Storing External Data**: The system must not store data from external sources in Slack's databases.
*   **Training on Customer Data**: The system must not train large language models (LLMs) on any customer data.
*   **Data Retention for Summaries**: The system must not store the generated "Search Answer" summaries; they are shown to the user and immediately discarded.
*   **Circumventing Permissions**: The system must not access any data that the user is not already permissioned to see in the source system.
*   **Exposing Data to Model Providers**: The architecture must prevent the LLM provider from ever having access to Slack customer data.

### 3. Risks and constraints

*   **Technical Constraints**: The system is architected as a federated, real-time system, which makes it dependent on the availability, performance, and API contracts of partner search APIs. It cannot use a pre-indexed data store for external content.
*   **Security and Privacy Constraints**: The entire design is driven by a strict set of security principles. Customer data must not leave Slack's trust boundary, and LLMs cannot be trained on it. The system must use an "escrow VPC" to isolate the LLM.
*   **Compliance Constraints**: The system must integrate with and reuse all of Slack's existing enterprise-grade compliance infrastructure, such as Encryption Key Management (EKM) and International Data Residency.
*   **Third-Party Dependencies**: The functionality relies on third-party partners (e.g., Google, GitHub) for their public search APIs and for implementing the OAuth protocol for secure authorization. It also depends on AWS for hosting the LLM infrastructure.

### 4. Metrics and loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Internal**: The user's permissioned content within Slack, including messages and knowledge.
*   **External**: Content from connected third-party applications. The initial integrations are with Google Drive and GitHub.

#### 5.2. Labeling strategy

The system uses Retrieval Augmented Generation (RAG) and does not rely on labeled data for training. The "data" is the contextual information retrieved in real-time from internal and external sources to answer a user's query.

#### 5.3. Available metadata

The primary metadata used is the user's Access Control List (ACL) in Slack and the permissions granted via OAuth for external systems. This ensures the system only retrieves content the user is authorized to access.

#### 5.4. Data quality issues

The system is designed to prevent data staleness. By using a federated, real-time approach that queries external sources on-demand, the system ensures that the data and associated permissions are always up-to-date with the source system. The article states, "staleness simply isn’t possible" with this architecture.

#### 5.5. ETL or feature store architecture

The system explicitly avoids ETL and indexing for external data. The architecture is a "federated, real-time approach" where data is fetched from partner APIs at query time. There is no persistent storage of external source data in Slack's databases.

### 6. Validation schema

[NO INFO]

### 7. Baseline solution

The baseline is the existing Slack search functionality, which operates only on content stored within Slack. The enterprise search system is an extension of this baseline, augmenting it with results from federated queries to external applications.

### 8. Errors and their analysis

[NO INFO]

### 9. Training pipelines

#### 9.1. Tooling and automation

The system does not involve training LLMs on customer data. It uses pre-trained, closed-source LLMs. The primary infrastructure components mentioned are:
*   **Cloud Platform**: AWS is used to host the LLMs.
*   **Containerization/Isolation**: LLMs are run in an "escrow VPC" to ensure data privacy and isolation from the model provider.

#### 9.2. CI/CD

[NO INFO]

### 10. Features

#### 10.1. Feature categories

This is a RAG system, where the "features" are the documents retrieved to serve as context for the LLM. These are not traditional ML features. The context is composed of:
*   **Slack Content**: Messages and other knowledge from within Slack that the user has access to.
*   **External Content**: Documents, files, issues, or other data retrieved in real-time from connected applications like Google Drive and GitHub, based on the user's permissions in those systems.

#### 10.2. Feature selection

The selection of context is performed at query time via the RAG process. The system retrieves relevant content based on the user's query from both Slack's internal search indexes and by making API calls to external search endpoints.

### 11. Measuring results

[NO INFO]

### 12. Integration and Serving

#### 12.1. API design

The system interacts with external sources via their public search APIs. It is an online, real-time system that is triggered by a user's search query within the Slack client.

#### 12.2. Infrastructure

*   **Serving Architecture**: The system is built on Slack's app platform and uses a federated approach. When a user searches, queries are sent to both Slack's internal search and the APIs of connected external applications.
*   **LLM Hosting**: Closed-source LLMs are hosted in a dedicated "escrow VPC" on AWS. This architecture ensures that the model provider never has access to customer data, and the data itself never leaves Slack's trust boundary.
*   **Authorization**: The system uses the OAuth protocol to allow users to securely authorize Slack to perform actions on their behalf in external systems. It specifically requests read-only scopes.
*   **Caching**: The Slack client may perform client-side caching of data between reloads to improve performance for features like filtering and previews. This is not a server-side data store.

#### 12.3. SLAs and fallback

*   **SLAs**: [NO INFO]
*   **Fallback**: [inferred] If an external API is unavailable or a user has not granted access, the search would likely fall back to providing results from Slack content only.

#### 12.4. Release cycle

[NO INFO]

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Day-to-day operational procedures

*   **Access Management**: The system is opt-in by design.
    *   Slack administrators must first enable an external source for their entire organization.
    *   Individual users must then explicitly grant Slack access to their account in the external system via an OAuth flow.
*   **Revocation**: Both administrators and individual users can revoke access at any time.
*   **Transparency**: The system shows admins and end-users the specific OAuth scopes it plans to request when they enable an external source, ensuring they know what authorizations are being granted.

#### 14.2. Retraining and ownership

*   **Retraining Cadence**: Not applicable, as a core principle is not to train LLMs on customer data. The system uses pre-trained models.