- Company: Netflix
- Title: For your eyes only: improving Netflix video quality with neural networks
- Technology area: Predictive ML
- Source URL: https://netflixtechblog.com/for-your-eyes-only-improving-netflix-video-quality-with-neural-networks-5b8d032da09c
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The problem is to improve the perceived video quality for Netflix members across millions of devices and varying network conditions. The specific focus is on the video downscaling step within Netflix's video encoding pipeline. Downscaling is necessary to create multiple resolutions (e.g., 1080p, 720p, 540p) from a high-quality source (e.g., 4K) to adapt streaming to different device screens and network bandwidths.

#### 1.2. Relevance & reasons

The conventional method for video downscaling uses standard resampling filters like Lanczos. Netflix identified an opportunity to improve video quality by replacing this conventional filter with a learned, neural network-based approach. This new approach, dubbed the "deep downscaler," aims to create a higher-quality downscaled representation that is tailored to Netflix's content and improves the end-to-end viewing experience.

The key advantages of this approach are:
*   **Improved Video Quality**: A learned downscaler can be optimized to preserve more detail and produce a sharper image after encoding and upscaling on the client device.
*   **Drop-in Solution**: The deep downscaler replaces an existing component in the encoding pipeline without requiring any changes to the video codecs or client-side devices. This allows for immediate benefits for all Netflix members.
*   **Independent Evolution**: As a distinct video processing block, the neural network component can be improved and evolved independently of the video codecs.

#### 1.3. Expectations

The system is expected to produce a downscaled video that, after being encoded, streamed, and upscaled on a member's device, results in a visually superior image compared to the traditional Lanczos downscaling method. The improvements should be noticeable to viewers, leading to better detail preservation and a sharper look. The solution must be computationally efficient enough to be deployed at Netflix's scale without incurring prohibitive costs.

#### 1.4. Previous work

The existing system used a conventional resampling filter, specifically Lanczos, for video downscaling. This is a standard, non-learned approach common in video processing.

#### 1.5. Usage volumes and patterns

The system is applied during the video encoding process for Netflix's entire catalog. This means it operates at a massive scale, processing a vast amount of video content to be streamed to millions of users worldwide. The solution must be integrated into all multi-CPU/GPU environments at scale.

### 2. Goals and anti-goals

#### 2.1. Goals

*   Improve end-to-end video quality for Netflix members.
*   Achieve measurable improvements in objective quality metrics (e.g., VMAF) and subjective visual tests.
*   Develop a solution that works as a "drop-in" replacement for the existing downscaler, requiring no changes on the client device side.
*   Ensure the solution is codec-agnostic and can be combined with different codecs (e.g., AV1, VP9).
*   Design a computationally efficient architecture to make deployment at scale economically viable.
*   Ensure no adverse streaming impact or device playback issues.

#### 2.2. Anti-goals

*   The solution should not require any changes to the video encoding standards or client-side playback logic.
*   The solution should not be tied to a specific video encoder or encoding implementation.
*   The solution should not introduce negative visual quality impacts or artifacts.

### 3. Risks and constraints

*   **Computational Cost**: Applying neural networks at Netflix's scale can lead to a significant increase in encoding costs. The solution must be highly efficient to be viable.
*   **Playback Compatibility**: Any change in the encoding pipeline risks introducing artifacts or bitstreams that could cause playback issues on the wide variety of devices that support Netflix. Extensive A/B testing is required to mitigate this.
*   **Quality Regression**: A poorly trained or designed model could result in a degradation of video quality for certain types of content or encoding settings.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Objective Metrics**:
    *   **VMAF Bjøntegaard-Delta (BD) rate gain**: A measure of compression efficiency improvement. The deep downscaler achieved an average gain of ~5.4% for VP9 encoding (with a bicubic upscaler).
    *   **VMAF-NEG BD rate gain**: A variant of VMAF focused on penalizing quality artifacts. The deep downscaler achieved a ~4.4% gain.
*   **Subjective Metrics**:
    *   **Preference-based visual tests**: Human subjects were shown videos processed with the baseline (Lanczos) and the deep downscaler and asked to choose their preference. The deep downscaler was preferred by ~77% of test subjects across a wide range of content and encoding recipes. Subjects reported "better detail preservation and sharper visual look."

#### 4.2. Online/business metrics

*   **Quality of Experience (QoE)**: Measured via A/B testing to confirm overall improvements in the streaming experience.
*   **Streaming Impact**: A/B tests were used to monitor for any adverse effects, such as increased playback errors or buffering. The tests showed QoE improvements without any adverse impact.

#### 4.3. Loss functions

The model is trained to minimize the **mean squared error (MSE)**. The training loop works as follows:
1.  A high-resolution video is passed through the deep downscaler network.
2.  The resulting lower-resolution video is upscaled back to the original resolution using a conventional, fixed upscaler (e.g., bicubic).
3.  The MSE is calculated between the upscaled video and the original high-resolution video.

This approach trains a robust downscaler that is not tied to a specific encoder, as the non-differentiable video codec is excluded from the training loop.

### 5. Data (Dataset)

#### 5.1. Data sources

The training data consists of high-quality source videos from the Netflix content library. The approach is designed to be tailored to the characteristics of Netflix content.

#### 5.2. Labeling strategy

This is an unsupervised/self-supervised problem. The "label" is the original high-quality video itself. The model learns to downscale in a way that minimizes reconstruction error after a fixed upscaling operation, requiring no manual labels.

#### 5.3. [NO INFO]

#### 5.4. [NO INFO]

### 6. Validation schema

*   **Objective Evaluation**: The model's performance was validated using objective metrics like VMAF BD-rate on a set of test videos. This was used to compare the deep downscaler against the Lanczos baseline.
*   **Subjective Evaluation**: Large-scale human subject studies (preference tests) were conducted to validate the perceptual improvements.
*   **A/B Testing**: A live A/B test was performed to measure the impact on real-world streaming sessions, monitoring QoE metrics and detecting any potential playback issues or quality degradations before a full rollout.

### 7. Baseline solution

The baseline solution is the traditional video downscaling method used in Netflix's pipeline prior to this project. This involves using a **conventional resampling filter, specifically Lanczos**. All objective and subjective improvements are measured against this baseline.

### 8. Errors and their analysis

*   The primary error mode of the baseline (Lanczos) that the deep downscaler addresses is suboptimal detail preservation, leading to a less sharp visual look after the full encode-decode-upscale cycle. Subjective tests confirmed the deep downscaler provided "better detail preservation and sharper visual look."
*   To avoid introducing new errors, the neural network architecture was carefully designed to prevent "negative visual quality impact."
*   A/B testing was used as a final check to detect any unforeseen errors, such as device playback issues or quality degradation on specific content, before full deployment.

### 9. Training pipelines

#### 9.1. Tooling

*   The inference engine is implemented as an **FFmpeg-based filter**.
*   For CPU execution, the filter leverages **oneDnn** to reduce latency.
*   The training and deployment pipeline is integrated with Netflix's internal platforms, including **Cosmos** (next-generation encoding platform) and **Titus** (container management platform).
*   The project involved collaboration with the **Netflix Metaflow team**, suggesting Metaflow may have been used for workflow orchestration [inferred].

#### 9.2. Pipeline steps

The training process is designed to create a downscaler that is robust and independent of a specific video codec.
1.  **Input**: High-quality source video.
2.  **Downscaling**: The source video is processed by the deep downscaler neural network.
3.  **Upscaling**: The downscaled video is immediately upscaled using a conventional, non-learned filter like bicubic.
4.  **Loss Calculation**: The mean squared error is computed between the upscaled video and the original source video.
5.  **Backpropagation**: The loss is used to update the weights of the deep downscaler network. The video codec is explicitly excluded from this loop as it is non-differentiable.

### 10. Features

The input to the model is the raw video signal (pixels). The model is a neural network architecture that learns the optimal transformation for downscaling.

*   **Model Architecture**:
    *   The network consists of two main building blocks: a **preprocessing block** to prefilter the video signal and a **resizing block** that produces the final lower-resolution output.
    *   The architecture is designed to be computationally efficient, using "just a few neural network layers."
    *   It employs an "adaptive network design" applicable to the wide variety of resolutions used in Netflix's encoding ladder.
*   **Feature/Channel Selection**:
    *   To improve efficiency and reduce computational load, the neural network-based scaling is applied only to the **luma (brightness) channel** of the video.
    *   The **chroma (color) channels** are downscaled using a standard Lanczos filter. This is effective because the human visual system is less sensitive to detail in color than in brightness.

### 11. Measuring results

#### 11.1. Offline evaluation

*   **Objective**: Compared the deep downscaler against the Lanczos baseline using VMAF BD-rate and VMAF-NEG BD-rate metrics. The deep downscaler showed gains of ~5.4% and ~4.4%, respectively, for VP9.
*   **Subjective**: Conducted preference-based visual tests where human subjects compared the two methods. The deep downscaler was preferred in ~77% of cases.

#### 11.2. A/B testing

*   **Hypothesis**: Replacing the Lanczos downscaler with the deep downscaler will improve member QoE without causing adverse streaming impact.
*   **Methodology**: A standard A/B test was run to compare the production performance of the new downscaler against the existing one. The test was used to measure QoE improvements and detect any device playback issues or quality regressions.
*   **Results**: The A/B tests confirmed QoE improvements with no adverse streaming impact, clearing the path for a full rollout.

### 12. Integration and Serving

This is an offline system integrated into the video encoding pipeline, not a real-time serving system.

#### 12.1. API design

The deep downscaler is implemented as an **FFmpeg-based filter**. It is invoked as part of a larger encoding workflow within a microservice.

#### 12.2. Infrastructure

*   **Platform**: The system is integrated into **Cosmos**, Netflix's next-generation cloud-based media encoding platform.
*   **Execution Environment**: The logic runs within a **Stratum function**, which is a serverless layer within a Cosmos microservice dedicated to stateless, computationally-intensive tasks.
*   **Compute**: The filter can run on both **CPU and GPU** environments. CPU execution is accelerated using the **oneDnn** library.
*   **Orchestration**: The underlying infrastructure is managed by **Titus**, Netflix's container management platform, which handles scaling across multi-CPU/GPU environments.

#### 12.3. Fallback strategies

[NO INFO]

### 13. Monitoring

*   **Pre-launch Monitoring**: A/B testing was the primary mechanism for monitoring the system's impact before full deployment. It was used to monitor for:
    *   **Quality Degradation**: Any drop in perceptual quality.
    *   **Device Playback Issues**: Errors, crashes, or visual artifacts on specific devices.
    *   **Adverse Streaming Impact**: Negative changes to metrics like rebuffering, playback delay, etc.
*   **Post-launch Monitoring**: [NO INFO], but it can be inferred that standard monitoring of encoding pipeline health and output quality continues.

### 14. Operations

*   **Deployment**: The deep downscaler is deployed as part of a **Cosmos encoding microservice**. This integration allows it to be used in multiple encoding workflows, such as generating final streams for Netflix members.
*   **Retraining**: [NO INFO]
*   **Incident Response**: [NO INFO]
*   **Future Work**: The success of the deep downscaler has paved the way for further applications of neural networks in video processing at Netflix. The team is exploring other use cases, such as **video denoising**, and looking for more efficient ways to apply NNs at scale.