**Company**: Wayfair
**Title**: From RGB to Descriptive Color Names: Wayfair's in-house color algorithms to improve customer shopping experience.
**Technology area**: Predictive ML
**Source URL**: https://www.aboutwayfair.com/careers/tech-blog/from-rgb-to-descriptive-color-names-wayfairs-in-house-color-algorithms-to-improve-customer-shopping-experience
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The core problem is the difficulty of accurately and consistently describing product colors using natural language. While colors can be precisely defined by numerical values like RGB, their corresponding names are often subjective and ambiguous. For example, a single RGB value like `#0F385C` can be described as "navy," "dark blue," or "midnight blue." Conversely, some RGB values like `#9999FF` can be described by different color names such as "blue" and "purple." This ambiguity creates challenges for product discovery and filtering in an e-commerce setting.

#### 1.2. Relevance & reasons

Solving this problem is critical for improving the customer shopping experience on Wayfair. Inaccurate, incomplete, or non-granular color tags lead to a sub-par color filtering experience, potentially causing customers to abandon the site. The key business drivers are:

*   **Accuracy**: Ensure customers searching for a "Blue Sofa" only see blue sofas, not black ones.
*   **Completeness**: Tag the millions of products in the Wayfair catalog with colors, preventing customers from missing out on products that lack color information.
*   **Granularity**: Allow customers to filter by specific shades, such as "Teal Sofa," to find the exact product they have in mind.

#### 1.3. Expectations

The system is expected to assign accurate, complete, and granular color names to each product in the catalog. The output should be a set of human-friendly color names that can be used to power the website's color filtering functionality.

#### 1.4. Previous work

The existing system relies on color tags provided by suppliers when they add products to the Wayfair catalog. These tags are acknowledged to be not always complete, accurate, or granular, which is the primary motivation for developing an in-house solution.

#### 1.5. Usage volumes and patterns

The system needs to operate on the scale of the entire Wayfair catalog, which consists of millions of products. The color tagging process is applied to product images to enrich the catalog data used for on-site search and filtering.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Develop a Color Taxonomy**: Create an algorithmically defined, hierarchical color palette that captures the relationship between RGB values and human-friendly color names.
*   **High Accuracy**: The generated color tags must be accurate. The target is to reduce the number of customers leaving the website due to poor color filtering. The system achieved an 88% acceptance rate in evaluation.
*   **High Completeness**: Tag all relevant products in the catalog to provide customers with a richer selection.
*   **High Granularity**: Provide color names at multiple levels of specificity (e.g., "blue" at a high level, "teal" at a more granular level) to support nuanced filtering.

#### 2.2. Anti-goals

*   **Relying solely on supplier data**: The system is explicitly designed to overcome the limitations of supplier-provided tags.
*   **Handling non-standard colors initially**: The initial scope does not include metallic-like colors or finishes. This is identified as future work.
*   **Robustness to image noise**: The initial version is not robust to noise in product images, such as shadows. For example, "white" products may be misclassified as "gray." Improving this is slated for future work.

### 3. Risks and constraints

*   **Subjectivity of Color**: Color perception is subjective, making it difficult to define a single "correct" color name. The system mitigates this by allowing multiple names and using a hierarchical taxonomy.
*   **Lack of Ground Truth**: There is no perfect ground truth dataset for color naming. The system uses a combination of supplier tags and human judgment as a proxy.
*   **Data Quality of Supplier Tags**: The supplier tags used for evaluation are known to be incomplete and sometimes inaccurate. This required a human-in-the-loop process to validate the model's predictions.
*   **Dependency on Human Annotation**: The system relies on human annotators to draw bounding boxes on product images to isolate specific product parts (e.g., upholstery, leg). This is a potential source of cost, latency, and error.
*   **Image Quality**: The system's predictions are sensitive to lighting conditions and shadows in product images, which can lead to incorrect color extraction.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Acceptance Rate**: The primary evaluation metric. A color tag is considered "acceptable" if it either matches the supplier-provided tag or is judged as acceptable by a human evaluator when it differs. The model achieved an **88% acceptance rate**.
    *   **Agreement with Supplier Tags**: A sub-metric, representing the percentage of model predictions that directly match supplier tags. The model achieved **63% agreement**.
*   **Delta-E (CIEDE2000)**: A color difference formula that quantifies the perceptual difference between two colors. It is used extensively in the creation of the color taxonomy to group similar RGB values.
    *   `delta-E < 2`: Negligible difference to the human eye.
    *   `delta-E > 10`: Distinguishable color difference.

#### 4.2. Online/business metrics

*   The stated business goal is to "reduce the number of customers leaving the website due to sub-par color filtering."

#### 4.3. Loss functions

The core of the system is an algorithmic pipeline for building a taxonomy, not a supervised model trained with a loss function. The key algorithms are clustering (K-means, Birch) and graph-based methods, which use **delta-E** as the distance metric to optimize cluster cohesion and separation.

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Product Imagery**: Images from the Wayfair catalog across various categories (bedding, rugs, upholstery, etc.).
*   **Human-Annotated Bounding Boxes**: Bounding boxes drawn by human annotators on product images to isolate specific product attributes like upholstery, legs, or frames. RGB values are extracted from within these boxes.
*   **Supplier-Provided Color Tags**: Color names provided by suppliers, used as a "pseudo ground truth" for evaluation.
*   **Open-Source Color Mappings**: A dataset of ~1200 unique pairs of RGB values and color names scraped from public sources like Wikipedia and ColorHexa. This is used to bootstrap the naming of the most granular color groups.
*   **Curated Basic Colors**: A set of 12 basic, unambiguous colors ("red", "green", "blue", "yellow", "purple", "pink", "black", "white", "orange", "brown", "gray", and "beige"). Each color is associated with ~30 RGB values curated by an internal team of designers.

#### 5.2. Labeling strategy

The system uses a multi-stage, algorithmic approach for labeling, which constitutes the creation of the color taxonomy.

1.  **Unsupervised Clustering**: RGB values from product images are clustered at multiple levels to form a hierarchy.
2.  **Bootstrapped Naming**: The most granular clusters (Level 4) are named by finding the nearest neighbors in the scraped open-source color mapping dataset.
3.  **Hierarchical Name Propagation**: Names are aggregated up the hierarchy from lower levels to higher levels.
4.  **Evaluation Labeling**: For evaluation, a human-in-the-loop (HITL) process is used. Predictions that do not match supplier tags are sent to human evaluators for a final judgment of "acceptable" or "not acceptable."

#### 5.3. Data quality issues

*   Supplier tags are often incomplete, inaccurate, or not granular enough.
*   Product images can contain noise, such as shadows, which affects the accuracy of RGB value extraction.

### 6. Validation schema

The system is validated using a human-in-the-loop (HITL) framework, not a traditional train/test split. This was chosen to address the lack of a reliable ground truth dataset and the subjectivity of color correctness.

The two-step evaluation process is as follows:
1.  **Comparison with Supplier Tags**: The model-predicted color tags are first compared against the existing supplier-provided tags for a given product. If they match, the prediction is considered correct. This accounts for 63% of cases.
2.  **Human Judgment**: For the remaining 37% of cases where the model's prediction does not match the supplier tag, the prediction is sent to a human evaluator. The evaluator determines if the model's predicted color is an acceptable description of the product, even if it differs from the supplier's tag.
3.  **Final Metric Calculation**: The overall "acceptance rate" is the percentage of predictions that passed either step 1 or step 2. The final reported acceptance rate is 88%.

### 7. Baseline solution

The de-facto baseline is the existing system of using **supplier-provided color tags**. The new algorithmic system is evaluated against this baseline. The evaluation showed that in cases of disagreement, human evaluators often preferred the model's prediction over the supplier's tag, indicating an improvement in quality and granularity.

### 8. Errors and their analysis

*   **Image-based Errors**: A significant source of error is noise in product imagery. The primary example cited is shadows causing "white" products to be incorrectly predicted as "gray." This indicates the model is sensitive to lighting conditions.
*   **Supplier Tag Inaccuracies**: The evaluation revealed many cases where the supplier tag was incorrect and the model's prediction was preferred by human judges. Examples include:
    *   Model: "Blue", Supplier: "Purple"
    *   Model: "Red", Supplier: "Orange"
    *   Model: "Green", Supplier: "Yellow"
*   **Color Ambiguity**: Some colors are inherently ambiguous and can belong to multiple parent categories (e.g., "teal" can be considered both "blue" and "green"). The taxonomy is designed to handle this with graph-based clustering at Level 2, but it can still lead to perceived errors if a user expects only one primary color.

### 9. Training pipelines

The "training" process is the algorithmic construction of the Wayfair Color Taxonomy. This is an offline, multi-level pipeline.

*   **Level 4 (Most Granular)**:
    *   **Algorithm**: K-means clustering on RGBs extracted from product image bounding boxes.
    *   **Parameters**: `k = 4055` to ensure the minimum pairwise distance between cluster centroids is `delta-E > 2` (visually distinguishable).
    *   **Naming**: Assign names from a scraped web dataset (Wikipedia, ColorHexa) if the `delta-E` distance is `< 3`.
*   **Level 3 (Granular, Narrow Spectrum)**:
    *   **Algorithm**: Birch clustering on Level 4 groups.
    *   **Parameters**: The distance from an RGB to its cluster centroid is at most `5 delta-E`.
    *   **Naming**: A Level 3 group aggregates the color names from its constituent Level 4 child groups.
*   **Level 2 (Granular, Wide Spectrum)**:
    *   **Algorithm**: A graph-based algorithm on Level 3 groups. Nodes are Level 3 groups, and an edge exists if the `delta-E` distance between their centroids is `< 10`. The algorithm iteratively identifies maximum size cliques.
    *   **Parameters**: The smallest clique size is 3. This allows a color to be tied to multiple parent colors (e.g., teal to blue and green).
    *   **Naming**: A Level 2 group aggregates the color names from its constituent Level 3 child groups.
*   **Level 1 (Most Basic)**:
    *   **Algorithm**: K-nearest neighbor search to map Level 2 RGBs to a predefined list of 12 basic colors.
    *   **Parameters**: `k = 9`. A Level 2 RGB is assigned to a Level 1 color if the similarity is above a 30% threshold, allowing for multi-parent assignment.
    *   **Naming**: The names are predefined: "red", "green", "blue", "yellow", "purple", "pink", "black", "white", "orange", "brown", "gray", and "beige".

*   **Tooling**: [NO INFO]

### 10. Features

*   **Primary Features**: RGB values extracted from product images.
*   **Feature Extraction**:
    1.  Human annotators draw bounding boxes on product images to isolate specific parts (e.g., upholstery).
    2.  Within each bounding box, **mini-batch k-means** with `k=5` is used to extract up to 5 dominant colors and their corresponding volumes (percentage of pixels). (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_060/img_009.jpg`)
*   **Future Features**: The team plans to explore other data sources and features to improve robustness, including:
    *   Supplier descriptions
    *   Digital swatches
    *   HSV spectrum
    *   Color histograms

### 11. Measuring results

#### 11.1. Offline evaluation methodology

The offline evaluation is based on the "acceptance rate" metric, calculated via a two-step HITL process described in Section 6. The key results are:
*   **63%** agreement with supplier tags.
*   **88%** final acceptance rate after human evaluation of the remaining 37% of cases.

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting format

The results are reported via the final acceptance rate metric. The article also includes qualitative examples of products where the model's prediction was preferred over the supplier's tag, demonstrating the model's superior performance in specific cases. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_060/img_010.jpg`)

### 12. Integration and Serving

The system is a batch pipeline that enriches the product catalog with color tags.

#### 12.1. API design

The system is an offline pipeline, not a real-time API. It takes product images as input and outputs color tags that are stored in the product catalog.

#### 12.2. Infrastructure

*   The pipeline for mapping extracted colors to the taxonomy uses **faiss**, a library for efficient similarity search.
*   The use of `faiss` is noted to be optimized for speed and memory, and it supports **GPU acceleration**, suggesting this step is computationally intensive.

#### 12.3. Color Tagging Pipeline

1.  **Dominant Color Extraction**: For a given product image and bounding box, extract up to 5 dominant RGB colors and their volumes using mini-batch k-means.
2.  **Nearest Neighbor Search**: For each dominant RGB color, use `faiss` to find the closest color in Level 4 of the pre-computed taxonomy.
3.  **Hierarchical Tagging**: Using the taxonomy's parent-child relationships, retrieve the corresponding color names at all four levels of granularity (Level 1 to Level 4). (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_060/img_009.jpg`)

#### 12.4. SLAs and fallback strategies

[NO INFO] (likely not applicable for a batch catalog enrichment process).

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Day-to-day operational procedures

[NO INFO]

#### 14.2. Retraining cadence

[NO INFO]

#### 14.3. Incident response and rollback procedures

[NO INFO]

#### 14.4. Non-engineering considerations

*   **Future Scope Expansion**: There is a plan to expand the system to handle metallic colors ("brass", "bronze", "gold", etc.) and finishes ("brushed", "satin", etc.). This will be handled by a separate "reflective model" using convolutional neural networks (CNNs), which is currently under development.
*   **Human-in-the-Loop**: The evaluation framework relies on human judgment, which implies an operational component for managing human annotation and review tasks.