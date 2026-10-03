**Company**: Picnic
**Title**: Adding Eyes to Picnic’s Automated Warehouses
**Technology area**: Computer Vision
**Source URL**: https://blog.picnic.nl/adding-eyes-to-picnics-automated-warehouses-8b6c70613e2f
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The problem originates in Picnic’s fully-automated fulfillment center in Utrecht, where thousands of totes move along more than 50 kilometers of conveyor belts daily. The in-house control software manages the logistics of these totes but lacks the ability to see their contents. This "blind spot" means that issues with the goods inside a tote are only discovered late in the process: at a picking station, by a delivery driver, or, in the worst-case scenario, by the customer.

#### 1.2. Relevance & reasons

The inability to inspect tote contents in real-time leads to several operational issues:
*   A product can bounce out of a tote.
*   Heavy items can squash fragile ones (e.g., a six-pack squashing tomatoes).
*   A shopper might accidentally place the wrong item in a bag (e.g., wrong flavor of yogurt).

Currently, these mistakes are mitigated using statistical safeguards and packing algorithms. The proposed computer vision system aims to detect these problems the moment they occur, allowing the system to reroute the affected tote for immediate correction. This would reduce manual labor, minimize delivery errors, and improve customer satisfaction.

The system is intended to address two main types of totes:
1.  **Order totes**: These are totes destined for a customer's doorstep.
2.  **Stock totes**: These totes are used to replenish stock for the order totes.

#### 1.3. Expectations

The system is expected to "see" problems as they happen and trigger an action, such as nudging the tote to a new destination for fixing. This implies a need for real-time or near-real-time detection and integration with the warehouse's tote control software.

#### 1.4. Previous work

The existing solution relies on "statistical safeguards and clever packing algorithms" to minimize errors. Manual counting of stock totes is also performed by shoppers to maintain inventory accuracy, but this process interrupts the picking flow.

#### 1.5. Usage volumes and patterns

*   **Volume**: Thousands of totes are processed daily.
*   **Infrastructure**: The system involves over 50 kilometers of conveyor belts.
*   **Speed**: Conveyor belts move at 1.5 meters per second.

### 2. Goals and anti-goals

#### 2.1. Goals

The primary goal is to add computer vision "eyes" to the warehouse to detect and act on issues within totes.

**Use Cases for Order Totes:**
*   Verify that the correct number of items has been placed.
*   Flag items that have landed in the wrong bag.
*   Spot obvious product mismatches, such as the wrong flavor of crisps.

**Use Cases for Stock Totes:**
*   Automatically count items and update stock inventory data.
*   Highlight damaged, expired, or incorrect items.
*   Assist quality-control teams in finding totes with bad items, moving beyond random sampling.

**Business Goals:**
*   Fewer manual recounts.
*   Fewer delivery errors.
*   Happier customers.

#### 2.2. Anti-goals

*   **Ultra-low latency:** The system does not need to provide an instantaneous response. A delay of a few seconds is acceptable because the tote takes time to travel to its next destination. This allows for more computationally intensive and potentially more accurate models to be used. The article states, "We are okay with waiting a few seconds before the result comes in."

### 3. Risks and constraints

*   **Data Quality Risk**: If the training data is noisy or the production image feed is inconsistent, even the best model will perform poorly. The article states this is "non-negotiable."
*   **Hardware & Environment Constraints**:
    *   Conveyor belts move at 1.5 m/s, creating a risk of motion blur in images.
    *   Product packaging can be reflective, interfering with image capture.
    *   Products may be at awkward angles.
    *   Totes may not interact well with the lighting setup.
*   **Model-Specific Risks**:
    *   **VLM Hallucination**: Vision Language Models (VLMs) can still hallucinate, providing incorrect information.
    *   **VLM Cost**: Costs can increase quickly if inference volumes are high or tasks become more complex.
    *   **VLM Fine-tuning**: Fine-tuning VLMs with new labeled data is described as "very hard and expensive at the time of writing."
    *   **Specialized Model Limitations**: Models like CountGD are excellent for counting but cannot perform other tasks like damage classification, requiring a multi-model pipeline.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Counting Accuracy**: The selection of models like CountGD implies that item counting accuracy is a key metric. A future bake-off is planned to compare CountGD and Gemini on a dataset to see which "counts products in a tote the best."
*   **General VLM Performance**: The article mentions MMMU scores as a general benchmark for VLM improvement over time.

#### 4.2. Online/business metrics

*   Reduction in manual recounts.
*   Reduction in delivery errors.
*   Customer satisfaction improvements [inferred].

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Primary Source**: Images of totes captured by cameras mounted on the conveyor belt system.
*   **Metadata**: Each image is paired with the tote's unique barcode, which allows matching the visual contents to inventory records.
*   **Image Types**: The pilot uses 2D color images. 3D cameras providing depth information are a potential future upgrade.

#### 5.2. Labeling strategy

*   **3D Data**: The article notes that with a 3D camera, "annotation is almost trivial, because depth draws a clear border around every object."
*   **VLM Approach**: The VLM strategy relies on zero-shot capabilities using textual prompts (e.g., "apples") and visual exemplars, reducing the need for extensive manual labeling.
*   **Fine-tuning**: The article mentions that fine-tuning VLMs requires labeled training data, though this process is currently difficult and expensive.

#### 5.3. Data quality issues and cleaning

*   **Identified Issues**: Motion blur, reflective packaging, awkward product angles, and inconsistent lighting.
*   **Mitigation**: The system requires that each tote is "perfectly visible, with minimal motion blur." This is achieved through engineered, stable, and uniform lighting above the belt. The article emphasizes that raw input images must be "clean, consistent, and traceable."

#### 5.4. ETL

The data pipeline involves:
1.  Capturing an image of the tote on the conveyor belt.
2.  Scanning the tote's unique barcode.
3.  Pairing the image with its barcode metadata.
4.  Sending the image and metadata for inference (either to an edge device or the cloud).

### 6. Validation schema

*   **Holdout Set**: A comparative evaluation is planned to "challenge CountGD and the Google Gemini model lineup against the same dataset," which implies the use of a common holdout test set.
*   **Other Details**: [NO INFO]

### 7. Baseline solution

*   **Model**: YOLO (specifically YOLOv10) is identified as a "traditional baseline for local computer vision."
*   **Rationale**: It is chosen for its balance between speed and accuracy, ease of modification ("easy to tinker with"), and its battle-tested, cloud-edge agnostic nature.
*   **Context**: While YOLO is a strong baseline, the article notes that its strength in low-latency scenarios is not a primary requirement for this project, suggesting more accurate models could be used given the flexible time budget.

### 8. Errors and their analysis

#### 8.1. Error taxonomy

*   **Data Capture Errors**:
    *   Blurry images due to motion.
    *   Missed barcode scans, leading to untraceable images.
    *   Poor visibility due to inconsistent lighting or reflective packaging.
*   **Model Errors**:
    *   **Geometric Ambiguity (2D)**: A 2D camera can struggle to distinguish between overlapping items.
    *   **Hallucination (VLM)**: VLMs may generate plausible but factually incorrect descriptions of tote contents.
    *   **Limited Scope (Specialized Models)**: A model like CountGD can only count objects and cannot detect damage, requiring additional models to cover all use cases.

#### 8.2. Business-level errors to be detected

*   Products that have bounced out of the tote.
*   Damaged products (e.g., "squashed tomatoes").
*   Incorrect items placed in a bag (e.g., "wrong flavour of yoghurt").
*   Incorrect item counts.
*   Damaged, expired, or incorrect items in stock totes.

### 9. Training pipelines

#### 9.1. Tooling

*   **Hardware**:
    *   **Edge**: Nvidia Jetson devices for local inference.
    *   **Cloud**: AWS is mentioned for cloud computing.
*   **Models/Frameworks**:
    *   YOLOv10
    *   CountGD
    *   VLMs (OpenAI's GPT family, Google's Gemini models)

#### 9.2. Pipeline stages

The article focuses on inference architecture choices rather than the training pipeline itself. It mentions that a VLM strategy is "orders of magnitude faster to implement" and allows for "blazingly fast prototyping."

#### 9.3. Experiment tracking and CI/CD

[NO INFO]

### 10. Features

#### 10.1. Feature categories

*   **Primary Feature**: The image of the tote's contents.
*   **Feature Modalities**:
    *   **2D Image**: A high-resolution color image. Chosen for the pilot.
    *   **3D Image**: Includes a depth channel, which provides the distance to each pixel. Considered for future upgrades.
*   **Metadata**: The tote's unique barcode, linked to inventory data.
*   **Prompting Features (for VLMs)**:
    *   Textual prompts (e.g., "apples").
    *   Visual exemplars.

#### 10.2. Feature selection

A key trade-off was made between 2D and 3D cameras for the pilot:
*   **2D Camera**:
    *   **Pros**: Budget-friendly, easy to install, captures high-quality color images, sufficient for barcode reading and label mismatches under controlled lighting.
    *   **Cons**: Struggles with overlapping items.
*   **3D Camera**:
    *   **Pros**: Separates overlapping products, makes annotation easier.
    *   **Cons**: Costs 2-3 times more, consumes more bandwidth, requires "painstaking calibration."

The project opted for the **2D camera** for the pilot, leveraging the engineered uniform lighting to ensure sharp, reliable images.

### 11. Measuring results

#### 11.1. Offline evaluation

*   A comparative study is planned to evaluate CountGD and Google Gemini models on the same dataset to determine the best performer for product counting.
*   General VLM progress is tracked via public benchmarks like MMMU scores.

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting format

[NO INFO]

### 12. Integration and Serving

#### 12.1. API design

*   For the VLM approach, the system would use vendor APIs. The article mentions that Gemini can turn a "single API call into object counts, bounding boxes and relationship descriptions."
*   Prompts must be carefully developed to ensure the VLM returns data in a consistent format.

#### 12.2. Infrastructure

Two main serving architectures are being considered:

1.  **Edge Computing**:
    *   **Architecture**: Run inference locally on a device like an Nvidia Jetson GPU mounted inside the camera cabinet.
    *   **Pros**: Reduces latency and network bandwidth usage.
    *   **Cons**: Requires deploying and maintaining more hardware in the warehouse; potentially longer development time.

2.  **Cloud Computing**:
    *   **Architecture**: A thin client on the edge captures and sends images to the cloud (e.g., AWS) for inference by large models like VLMs.
    *   **Pros**: Decouples the system from on-premise GPUs, allows scaling model size without hardware changes, faster prototyping, and ability to leverage rapid VLM improvements.
    *   **Cons**: Higher latency (though acceptable), potential for high costs at scale, model hallucinations.

The project is leaning towards the cloud-based VLM trajectory, citing the rapid decrease in cost and increase in capability of these models.

#### 12.3. SLAs, latency, and fallback

*   **Latency**: A response time of a few seconds is acceptable. During testing, Gemini 2.5 Flash took **3 to 4 seconds** to respond. Potential optimizations include shorter prompts, image compression, and caching.
*   **Fallback Strategy**: If the AI detects a problem, the system will trigger a physical action:
    *   The tote is rerouted to a special station for human inspection.
    *   The stock inventory data is adjusted.

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Retraining and model updates

*   The cloud/VLM approach is favored for its "plug and play model upgrades over time."
*   Fine-tuning VLMs on new, custom-labeled data is considered an option for the future but is currently difficult and expensive.

#### 14.2. Incident response

*   When the system flags a faulty tote, it is sent to a dedicated station for a human operator to inspect and resolve the issue.
*   The system can also be used to trigger updates to inventory data directly.

#### 14.3. Stakeholder integration

*   The system will help quality-control teams proactively find totes with bad items, replacing the current method of random sampling or relying on shopper reports.