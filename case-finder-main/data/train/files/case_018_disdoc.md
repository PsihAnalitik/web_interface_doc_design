# Adopting Vespa for Personalized Second-Hand Fashion Recommendations

**Metadata**
- **Company**: Vinted
- **Title**: Adopting the Vespa search engine for serving personalized second-hand fashion recommendations at Vinted
- **Technology Area**: Predictive ML / Recommender Systems
- **Source URL**: https://vinted.engineering/2023/10/09/adopting-vespa-for-recommendation-retrieval/
- **Content Type**: Article

---

### 1. Problem definition

**i. Origin**
Vinted, a large second-hand fashion marketplace, implements a 3-stage recommender system to curate personalized listing recommendations for the homepage. The system must distill a tailored selection from millions of available listings based on both explicit user preferences (e.g., clothing sizes) and implicit preferences (e.g., historical interactions).

**ii. Relevance & reasons**
The first stage of the system is responsible for the initial recall of relevant content. The previous implementation used the Faiss library, which presented several critical limitations:
- **Statelessness**: Faiss was used as a read-only index in a stateless Kubernetes service, requiring periodic rebuilds and redeployments to handle new uploads or removals of sold/deleted items.
- **Lack of Pre-filtering**: Faiss does not support ANN search with metadata pre-filtering. Filtering occurred as a post-processing step on a fixed-length list. If the top-k items did not match user-specified filters (e.g., brand, size), users would see no recommendations.

**iii. Expectations**
- **Latency**: The first stage must recall relevant content in $< 100$ ms.
- **Functionality**: The system must support metadata pre-filtering to ensure recommendations are always returned regardless of user-set filters.
- **Scalability**: Ability to handle millions of listings and high query throughput.

**iv. Previous work**
- **Faiss**: Used for initial iterations to prove value but failed to meet operational and filtering requirements.

**v. Usage volumes and patterns**
- **Dataset size**: Benchmarks were conducted with $\sim 1\text{M}$ documents.
- **Embedding size**: 256-dimension float32 vectors.

---

### 2. Goals and anti-goals

**i. Goals**
- Implement a database solution that manages data and indices automatically.
- Enable Approximate Nearest Neighbor (ANN) search with metadata pre-filtering.
- Maintain low-latency retrieval (P99 $\approx 50$ ms).
- Support real-time data updates for newly uploaded or sold items.

**ii. Anti-goals**
- **Exact Search**: The system does not prioritize exact nearest neighbor search if it significantly increases latency or resource usage without a proportional increase in user satisfaction.

---

### 3. Risks and constraints

- **Technical Constraints**: Need for a system that supports both dense (vector) and sparse search techniques.
- **Licensing**: Vinted prefers truly open-source licensed software (Apache 2.0).
- **Organizational Constraints**: The team had no prior experience with Vespa.
- **Dependencies**: Reliance on Google Cloud Platform (GCP) infrastructure.

---

### 4. Metrics and loss functions

**i. Offline Metrics**
- **Indexing Throughput**: Measured as document indexing speed.
- **Query Throughput**: Measured in Requests Per Second (RPS) before CPU saturation.
- **Latency**: P99 response time.
- **Recall**: The proportion of matching documents retrieved by approximate search compared to exact search (measured at 60-70% for the chosen HNSW parameters).

**ii. Online/Business Metrics**
- **User Engagement/Satisfaction**: Measured via A/B testing and qualitative member testimonies.
- **P99 Latency**: Monitored in production (target $\sim 50$ ms).

**iii. Loss Functions**
- **Two-Tower Model**: The model is trained such that the distance between a user's embedding and a listing's embedding represents the affinity or relevance for the user-item pair. [NO INFO] on the specific loss function (e.g., Triplet Loss, Contrastive Loss).

---

### 5. Data (Dataset)

**i. Data Sources**
- **Listing Metadata**: Brand, price, size, and unstructured data (photos).
- **User Interactions**: Historical sequences of clicks, favorites, and purchases.

**ii. Labeling Strategy**
- **Implicit Labels**: Derived from user interactions (clicks, favorites, purchases).

**iii. Data Quality and ETL**
- [NO INFO]

---

### 6. Validation schema

- **A/B Testing**: Used to compare Vespa against the previous system and to compare Approximate Search vs. Exact Search.
- [NO INFO] on train/test split or holdout set strategies.

---

### 7. Baseline solution

**i. Baseline**
- **Faiss**: Used as the initial ANN search baseline.
- **Elasticsearch**: Evaluated as a mature alternative during the technology selection phase.

**ii. Comparison Framework**
Benchmarks were performed on a single GCP `n1-standard-64` VM (64 vCPUs, 236 GB) using Docker containers. HNSW hyperparameters were kept consistent across platforms.
- **Vespa vs. Elasticsearch Results**:
    - **Indexing Throughput**: Vespa was 3.8x higher.
    - **Query Throughput**: Vespa handled 8x more RPS before CPU saturation.
    - **Latency**: Vespa P99 was 26ms vs. Elasticsearch's 110ms at 250 RPS.

---

### 8. Errors and their analysis

**i. Error Taxonomy**
- **Latency Spikes**: A small portion of queries exceeded the 150ms timeout.

**ii. Diagnostic Approaches**
- **Tracing**: Used Vespa's built-in tracing tool to identify the root cause of problematic queries.
- **Community Collaboration**: Issues were escalated via Vespa Slack and GitHub, leading to official fixes in subsequent releases.

---

### 9. Training pipelines

**i. Model Architecture**
- **Two-Tower Model**:
    - **Listing Tower**: Generates vector representations from listing metadata and photos.
    - **User Tower**: Generates embeddings based on a sequence of past interactions.

**ii. Tooling**
- **Deployment**: Docker containers.
- **Infrastructure**: Google Cloud Platform.
- [NO INFO] on specific training frameworks (e.g., PyTorch, TensorFlow) or CI/CD pipelines.

---

### 10. Features

**i. Feature Categories**
- **Listing Features**: Brand, price, size, and image-based embeddings.
- **User Features**: Sequence of historical interactions (clicks, favorites, purchases).

**ii. Selection Criteria**
- [NO INFO]

---

### 11. Measuring results

**i. Offline Evaluation**
- Benchmarking of throughput and latency on a 1M document dataset.
- Recall measurement (Approximate vs. Exact search).

**ii. A/B Test Design**
- **Hypothesis**: Exact search (higher accuracy) would increase user satisfaction more than the cost of increased latency.
- **Splitting**: 50% of users received approximate search; 50% received exact search.
- **Results**: P99 latency increased from $\sim 50$ms to $\sim 70$ms (+40%). User satisfaction did not increase enough to justify the resource usage.

---

### 12. Integration and Serving

**i. Serving Architecture**
- **Retrieval Stage**: Vespa serves as the first-stage recall system.
- **Configuration**: Content cluster with 3 groups; each server stores a complete copy of the dataset to scale query throughput.
- **Hardware**: 3 servers with 56 CPU cores each for high availability (HA).

**ii. API and Querying**
- **Query Logic**: Uses `nearestNeighbor` queries with a `targetHits` parameter.
- **Switching Logic**: Toggled via the `approximate:true/false` parameter.

**iii. SLAs and Fallbacks**
- **Query Timeout**: Set at 150ms.

---

### 13. Monitoring

**i. Engineering Metrics**
- **Prometheus/Grafana**: Vespa exposes metrics in Prometheus format for real-time monitoring.
- **Latency**: Monitoring P99 latency.

**ii. Model/Data Quality**
- [NO INFO]

---

### 14. Operations

**i. Operational Procedures**
- **Configuration Management**: All configuration is controlled via the deployment of the application package; running servers are not modified manually.
- **Deployment**: Managed via Docker and environment variables (e.g., `VESPA_CONFIGSERVERS`).

**ii. Retraining and Maintenance**
- **Real-time Updates**: Vespa's real-time data update capability is used to manage the index.

**iii. Incident Response**
- Use of tracing for debugging and collaboration with the vendor (Vespa team) for bug fixes.