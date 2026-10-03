- Company: Netflix
- Title: Using Machine Learning to Improve Streaming Quality at Netflix
- Technology area: Predictive ML
- Source URL: https://netflixtechblog.com/using-machine-learning-to-improve-streaming-quality-at-netflix-9651263ef09f
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The core problem is to provide a high-quality streaming experience for a global and diverse audience. A "one size fits all" solution for streaming video is increasingly suboptimal due to variations in:
*   **Networks**: Cellular networks are more volatile than fixed broadband; some markets experience higher congestion.
*   **Devices**: Over a thousand different device types (laptops, tablets, Smart TVs, mobile phones, streaming sticks) with varying capabilities and hardware.
*   **Viewing Behavior**: User behavior on mobile devices differs from that on Smart TVs.

This document describes four distinct ML applications designed to address these challenges:
1.  **Network Quality Prediction**: Characterizing and predicting network throughput to inform streaming decisions.
2.  **Video Quality Adaptation**: Dynamically selecting the optimal video quality during playback to balance quality and stability.
3.  **Predictive Caching**: Predicting what a user will play next to pre-cache content on their device.
4.  **Device Anomaly Detection**: Automatically detecting and prioritizing performance or reliability issues on specific devices.

#### 1.2. Relevance & reasons

Improving streaming quality is central to Netflix's strategy for member retention and expansion into new markets. Machine learning is leveraged because:
*   **Sufficient Data**: Data is collected from every viewing session across all members.
*   **High-Dimensionality**: The data is high-dimensional, making it difficult to hand-craft informative variables.
*   **Complex Structure**: The data contains rich structures from underlying phenomena like collective network usage, human preferences, and device hardware capabilities.

The existing process for device anomaly detection is described as a "manually intensive process," and ML is expected to drive "substantial efficiency gains" for the device reliability team.

#### 1.3. Expectations

The overall goal is to optimize the "quality of experience" (QoE) for the user. This involves balancing several competing factors:
*   Minimizing the initial wait time for video to start playing.
*   Maximizing the overall video quality (bitrate).
*   Minimizing playback interruptions (rebuffers).
*   Minimizing perceptible fluctuations in video quality during playback.

For device anomaly detection, the expectation is to reduce the volume of false-positive alerts requiring manual investigation while maintaining a low false-negative rate.

#### 1.4. Previous work

*   **Alerting Frameworks**: Existing alerting frameworks are used for device anomaly detection but suffer from a trade-off between false positives and false negatives. A "liberal" trigger creates too many false positives, while a "strict" trigger misses real problems.
*   **Adaptive Streaming**: The article references prior research by Netflix colleagues on adaptive streaming algorithms, which form the foundation for the video quality adaptation problem.

#### 1.5. Usage volumes and patterns

*   **Scale**: The system serves over 117 million members worldwide (as of 2018).
*   **Global Reach**: Well over half of the members live outside the United States.
*   **Device Ecosystem**: The service operates on over a thousand different types of devices.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Primary Goal**: Optimize the Quality of Experience (QoE) for users by balancing video quality, start time, and playback interruptions.
*   **Network Quality Prediction**: Accurately characterize and predict the distribution of expected network throughput.
*   **Video Quality Adaptation**: Learn an optimal control algorithm to select video quality that maximizes QoE, addressing the delayed and sparse feedback signals (credit assignment problem).
*   **Predictive Caching**: Maximize the likelihood of caching the content a user will actually play, subject to device constraints. This has a direct goal of reducing the time spent waiting for video to start.
*   **Device Anomaly Detection**: Reduce the overall volume of alerts requiring manual investigation while maintaining an acceptably low false-negative rate. Increase the efficiency of the device reliability team.

#### 2.2. Anti-goals

*   **Avoid "Solution in Search of a Problem"**: The use of ML should be justified by tangible improvements over simpler methods.
*   **Avoid Over-Optimization on a Single Metric**: The system should not aggressively optimize for the highest video quality if it increases the risk of rebuffers, nor should it be so conservative that it sacrifices quality unnecessarily. The trade-offs between QoE metrics must be managed.

### 3. Risks and constraints

*   **Data Sparsity and Delay**: The feedback signal for a video quality adaptation decision is delayed and sparse. For example, an aggressive switch to a higher bitrate may only lead to a rebuffer much later, making credit assignment difficult.
*   **Noisy Data**: Network throughput measurements are "quite noisy and fluctuate within a wide range."
*   **Unpredictable Events**: Network drops can be caused by unpredictable real-world events (e.g., "a microwave turning on or going through a tunnel").
*   **Resource Constraints**: Predictive caching is constrained by the device's cache size and available bandwidth.
*   **Scale and Diversity**: The system must operate across a massive, heterogeneous ecosystem of over 1,000 device types, diverse network conditions, and global user behaviors.
*   **Manual Labeling Bottleneck**: The device anomaly detection model relies on human determination of whether an alert was "real and actionable," which can be a bottleneck.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Predictive Caching**: The model's likelihood of caching what the user actually ended up playing (e.g., hit rate, precision).
*   **Device Anomaly Detection**:
    *   False Positive Rate: To be minimized to reduce unnecessary manual investigation.
    *   False Negative Rate: To be kept at an "acceptably low" level to avoid missing real problems.
    *   Alert Volume Reduction: The overall reduction in alerts sent to the reliability team.

#### 4.2. Online/business metrics

The overall Quality of Experience (QoE) is measured through a combination of online metrics:
*   **Initial Wait Time**: The time spent waiting for video to play. Predictive caching has shown "substantial reductions" in this metric.
*   **Overall Video Quality**: The average bitrate or resolution experienced by the user.
*   **Rebuffers**: The number of times playback pauses to load more video into the buffer.
*   **Quality Fluctuation**: The amount of perceptible fluctuation in video quality during playback.
*   **Team Efficiency**: For device anomaly detection, the goal is to drive "substantial efficiency gains for Netflix’s device reliability team."

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Session Data**: For every viewing session, Netflix observes:
    *   Network conditions (e.g., throughput traces).
    *   Device conditions.
    *   User experience aspects (e.g., video quality delivered, rebuffers).
*   **Historical Data**: Longer-term historical information about specific networks and devices.
*   **User Interaction Data**: For predictive caching, this includes:
    *   Viewing history (e.g., series progression).
    *   Recent user interactions.
    *   Other contextual variables.
*   **Alert & Label Data**: For device anomaly detection, the dataset consists of:
    *   History of triggered alerts from an alerting framework.
    *   Human-provided labels determining if an alert was "real and actionable."

#### 5.2. Labeling strategy

*   **Predictive Caching**: The label is the content that the user actually played. This is a form of implicit feedback.
*   **Device Anomaly Detection**: Labels are generated by a human from the device reliability team, who determines if a triggered alert corresponds to a "real and actionable" issue.

#### 5.3. Data quality issues and cleaning

*   Network throughput data is acknowledged to be "quite noisy and fluctuate within a wide range."

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

#### 6.1. Train/validation/test split

[NO INFO]

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets

*   **Root Cause Analysis**: The article mentions using statistical modeling to control for covariates like "an internal A/B experiment or change that was rolled out" to determine the root cause of an issue. This implies that A/B test groups can serve as a form of holdout for causal analysis.

### 7. Baseline solution

*   **Video Quality Adaptation**: The implicit baseline is a "one size fits all" solution that does not adapt to diverse and fluctuating conditions.
*   **Device Anomaly Detection**: The baseline is an alerting framework with simple, manually-set triggers. This leads to a difficult trade-off:
    *   A "liberal" trigger (high sensitivity) results in too many false positives.
    *   A "strict" trigger (high specificity) results in missing real problems (false negatives).

### 8. Errors and their analysis

*   **Video Quality Adaptation**:
    *   **Credit Assignment Problem**: An aggressive switch to higher quality might deplete the buffer over time and cause a rebuffer event later. It is difficult to attribute this failure back to the specific decision that caused it.
*   **Device Anomaly Detection**:
    *   **False Positives**: Alerts that are triggered but do not correspond to a real, actionable problem. These lead to wasted manual investigation time for the device reliability team.
    *   **False Negatives**: Real issues that are not detected by the system.
    *   **Root Cause Ambiguity**: Even when an issue is correctly identified, determining the root cause is challenging. The article poses several questions for root cause analysis: "Was it due to a fluctuation in network quality on a particular ISP or in a particular region? An internal A/B experiment or change that was rolled out? A firmware update issued by the device manufacturer?"
*   **Gradual Degradation**: The system must be able to detect gradual trends in device quality that accumulate over time, which may not be noticeable after any single change (e.g., a series of UI updates slowly degrading performance).

### 9. Training pipelines

*   **Model Types**: The article mentions "statistical models," "machine learning techniques," "supervised learning," and "reinforcement learning."
    *   **Network Prediction**: "complex models that combine temporal pattern recognition with various contextual indicators."
    *   **Video Quality Adaptation**: Reinforcement learning is mentioned as having "great potential" to solve the credit assignment problem.
    *   **Predictive Caching**: Formulated as a "supervised learning problem."
    *   **Device Anomaly Detection**: A model is trained to "predict the likelihood that a given set of measured conditions constitutes a real problem."
*   **Tooling**: [NO INFO]
*   **Automation**: [NO INFO]

### 10. Features

*   **Network Quality Prediction**:
    *   Temporal throughput data (e.g., "last 15 minutes of data").
    *   Longer-term historical information about the network and device.
    *   Contextual indicators.
    *   Data provided from the server.
*   **Predictive Caching**:
    *   Viewing history (e.g., which episode of a series is next).
    *   Recent user interactions.
    *   Contextual variables.
*   **Device Anomaly Detection & Root Cause Analysis**:
    *   "A given set of measured conditions" that trigger an alert.
    *   Covariates for root cause analysis:
        *   Network quality on a particular ISP or region.
        *   Internal A/B experiment status.
        *   Firmware update versions.
        *   Device group or specific model identifiers.

### 11. Measuring results

#### 11.1. Offline evaluation

*   **Device Anomaly Detection**: The model's performance is evaluated by its ability to achieve "large reductions in overall alert volume while maintaining an acceptably low false negative rate."

#### 11.2. A/B testing

*   A/B tests are mentioned as a potential root cause for device performance issues. Statistical modeling is used to control for the effect of these experiments when analyzing anomalies. [inferred] This suggests that the impact of new models or logic changes would be measured via A/B testing against the existing systems.

#### 11.3. Reporting

*   **Predictive Caching**: The system has demonstrated "substantial reductions in the time spent waiting for video to start."
*   **Device Anomaly Detection**: The system has achieved "large reductions in overall alert volume."

### 12. Integration and Serving

*   **Video Quality Adaptation**: The "adaptive streaming algorithms are responsible for adapting which video quality is streamed throughout playback." This implies an **on-device** model that makes real-time decisions based on current network and buffer conditions.
*   **Predictive Caching**: The model predicts what a user will play "in order to cache (part of) it on the device before the user hits play." This is also an **on-device** system, where predictions are used to trigger downloads.
*   **Device Anomaly Detection**: This appears to be an **offline batch system**. It analyzes aggregated data, and the model's output is a prioritized list of alerts for the "device reliability team" to investigate manually.
*   **Infrastructure**: The system must support over a thousand different device types, which presents a significant integration and maintenance challenge. Devices are constantly entering the ecosystem and receiving firmware updates.

### 13. Monitoring

*   **System Purpose**: The "Device Anomaly Detection" system is itself a meta-monitoring system. It monitors for:
    *   Startup failures ("app will not start up properly").
    *   Playback inhibition or degradation.
    *   Gradual trends in device quality over time.
*   **Alerting**: An alerting framework is used to surface potential issues. The ML model then sits on top of this framework to prioritize alerts and reduce false positives.
*   **Drift**: The system is designed to detect changes caused by firmware updates, Netflix application changes, or gradual performance degradation, which are forms of concept drift.

### 14. Operations

*   **Ownership**: The "device reliability team" is the primary user and operator of the device anomaly detection system. They perform manual investigations based on the model's prioritized alerts and provide the labels (feedback) used to train the model.
*   **Incident Response**: The anomaly detection system is a key part of the incident response workflow, helping to surface, prioritize, and determine the root cause of user-facing issues.
*   **Retraining**: The use of human feedback ("ultimate determination... of whether or not the issue was in fact real") to train the anomaly detection model implies a feedback loop that could be used for periodic retraining. [inferred]
*   **Rollback**: [NO INFO]