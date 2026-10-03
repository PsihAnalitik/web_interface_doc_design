**Company**: Canva
**Title**: Image replacement in Canva designs using reverse image search
**Technology Area**: Computer Vision
**Source URL**: https://www.canva.dev/blog/engineering/image-replacement-in-canva-designs-using-reverse-image-search/
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The core problem is automating the replacement of images within Canva's design templates. This is a necessary part of the content quality control process. A primary use case is when a partnership with a third-party media library expires, requiring all content from that library used in Canva templates to be replaced with suitable, IP-safe alternatives.

#### 1.2. Relevance & reasons

The manual process of finding and replacing images is a lengthy and resource-intensive task. Automating this process with a reverse image search system is intended to significantly reduce the manual effort and time required, thereby improving the efficiency of maintaining a high-quality media library for Canva's users.

#### 1.3. Expectations

The system is expected to function as an image-to-image search tool that suggests replacements based on visual similarity. The key product requirements are:
*   **High-Quality Similarity:** The suggested images must be visually similar to the original. Similarity is defined by a hierarchy of attributes:
    1.  **Subject:** The primary object or theme of the image must be preserved (e.g., an apple replaced with another apple).
    2.  **Color and Tone:** Finer-grained details like a red apple being replaced by another red apple.
    3.  **Composition:** Less critical but important attributes like subject positioning, background, and the emotion conveyed.
*   **IP Safety:** All suggested replacement images must be intellectual property (IP)-safe.
*   **Aspect Ratio:** The system must account for the image's aspect ratio, as this is crucial for maintaining the integrity of a design template.
*   **User Interface:** The suggestions are presented to internal template designers via the "Template Assistant" UI, which shows the top 8 similar images for a flagged asset.

#### 1.4. Previous work

Several existing internal systems were evaluated and deemed unsuitable for this specific task:
*   **Recommendation Engine:** This system was not used because its rankings are based on factors like popularity and design context, not purely on visual similarity. The resulting suggestions were not similar enough.
*   **Perceptual Hash System:** This system finds potential duplicate images. It was rejected because duplicates are considered "too similar" for this use case; if an image is being removed, its duplicates likely need to be removed as well, resulting in no valid suggestions.
*   **Text-to-Image Search:** This was inappropriate because image metadata (used by this search) often fails to capture nuanced visual features like the number of subjects, key colors, and image emotion.
*   **AI-Generated Images:** This option was ruled out because the generated images could not be guaranteed to be IP-safe.

#### 1.5. Usage volumes and patterns

*   **Corpus Size:** The system must search across Canva's media library of over 150 million images.
*   **Users:** The primary users are Canva's internal professional template designers.
*   **Update Frequency:** The system must stay up-to-date with frequent changes in the media library.

### 2. Goals and anti-goals

#### 2.1. Goals

*   Given an input image, suggest the most visually similar, IP-safe replacement images available in Canva's library.
*   The search must scale to over 150 million images.
*   The system's index must reflect the current state of the media library.
*   The system must support filtering on metadata fields, specifically aspect ratio.
*   The solution should be designed for reusability and extensibility for other future applications.

#### 2.2. Anti-goals

*   The system should not suggest exact duplicates of the image being replaced.
*   The system should not rank suggestions based on popularity or general design context.
*   The system must not use generative AI to create replacements, due to IP safety constraints.

### 3. Risks and constraints

*   **Technical Risks:** The chosen embedding model may not perform equally well across all types of images. The article notes that the selected model (DINOv2) is weaker for graphics, cartoons, and images with text compared to photographs.
*   **Data Constraints:** The system must only use images from Canva's library that are confirmed to be IP-safe.
*   **Architectural Constraints:** The solution must align with Canva's recommended design approaches, which ruled out costly, high-maintenance solutions like a dedicated machine with a huge amount of RAM for an in-memory vector database.
*   **Cost Constraints:** Cost was a significant factor in deciding to use a third-party external vector database over building one or using a large in-memory solution.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

A qualitative evaluation was performed to select the best model. No quantitative offline metrics (e.g., mAP, Recall@K) are mentioned.
*   **Methodology:** For a sample of 200 query images, the top 3 nearest neighbors from each candidate model were generated.
*   **Evaluation Criteria:** Engineers and designers manually reviewed the results, judging them against the defined image similarity hierarchy (subject, color/tone, composition).
*   **Selected Model:** DINOv2 was chosen as the most suitable model based on this qualitative assessment.

#### 4.2. Online/business metrics

*   **Designer Efficiency:** The primary business metric is the speed of the image replacement workflow. Initial pilots with professional designers showed a **4.5x increase in the speed of image replacement** when using the suggestions compared to performing a regular search.

#### 4.3. Loss functions

The system uses pre-trained models. The article does not mention any fine-tuning, so no specific loss function was implemented for this project. The chosen model, DINOv2, was trained using a self-supervised objective (masked image modeling).

### 5. Data (Dataset)

#### 5.1. Data sources

The search corpus is Canva's internal media library, which contains over 150 million images.

#### 5.2. Labeling strategy

This is an unsupervised similarity search problem, so no labeled training data was created. For model evaluation, a qualitative assessment was performed by internal engineers and designers on a sample of 200 images, effectively creating a "golden set" for evaluation.

#### 5.3. Available metadata

*   **Aspect Ratio:** Explicitly mentioned as a metadata field used for filtering search results.
*   **Text/Symbols:** The "Future Work" section proposes extracting text or symbols from images and storing them as metadata fields to improve search for graphical content.

#### 5.4. Data quality issues

*   The core problem addresses a data quality issue: removing images that are no longer licensed for use.
*   The model's performance varies by image type. The DINOv2 model was trained on a dataset (LVD-142M) composed mainly of photographs, leading to weaker performance on non-photorealistic images like cartoons, drawings, and symbols.

#### 5.5. ETL

The system requires an ETL process to keep the search index current:
1.  Extract image embeddings from all 150 million+ images in the library using the DINOv2 model.
2.  Ingest the embeddings and associated metadata into an external vector database.
3.  This process must run continuously or frequently to reflect real-time changes in the media library.

### 6. Validation schema

#### 6.1. Train/validation/test split

A formal train/val/test split was not used as no model was trained. The validation process was designed for model selection:
*   **Evaluation Set:** An initial set of 50,000 images was selected from the Canva library. Embeddings were generated for these images using each candidate model.
*   **Query Set:** A sample of 200 images was used as queries.
*   **Validation Method:** The top 3 nearest neighbors for each of the 200 query images were retrieved and manually assessed for quality.

#### 6.2. Cross-validation

[NO INFO]

#### 6.3. Holdout sets

The 200-image sample served as a holdout set for the qualitative comparison and selection of the final embedding model.

#### 6.4. Leakage risks

[NO INFO]

### 7. Baseline solution

Several potential solutions were considered as baselines before building a new system. All were rejected:
*   **Internal Recommendation Engine:** Not purely similarity-based.
*   **Internal Perceptual Hash System:** Finds duplicates, which are too similar.
*   **Internal Text-to-Image Search:** Metadata lacks nuanced visual detail.

During model selection, a composite approach was also tested as a baseline against end-to-end vision models:
*   **GPT4o + CLIP:** An image was sent to GPT4o to generate a textual description, which was then used to perform a text-to-image search against a CLIP vector database. This approach was found to be the least successful, as it failed to capture secondary subjects, coloring, and tones.

### 8. Errors and their analysis

*   **Error Taxonomy:** The primary source of error is the model's weaker performance on specific categories of images. The system produces strong results for photos but underwhelming results for graphics.
*   **Analysis of Weaknesses:**
    *   **Image Type:** The system is weaker for images containing text, symbols, or non-realistic imagery like cartoons and drawings.
    *   **Examples:** The article shows examples where a graphic with the text "MAY" is replaced by a photo of a flower, and an icon of a person is replaced by a photo of a person. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_015/img_006.png`)
*   **Root Cause Hypothesis:**
    1.  **Training Data Mismatch:** The DINOv2 model was pre-trained on LVD-142M, a dataset primarily composed of photographs, not graphics or symbolic images.
    2.  **Training Task Mismatch:** DINOv2's training objective (related to object, texture, and scene categorization) is not optimized for symbol recognition tasks.

### 9. Training pipelines

The system is an inference-only system using a pre-trained model. There is no training pipeline. The data processing pipeline consists of:
*   **Tooling:**
    *   **Embedding Models Evaluated:** DINOv2, CLIP, ViTMAE, DreamSim, CaiT.
    *   **Prototyping:** The Faiss library was used for an in-memory vector database during experimentation.
    *   **Production:** A third-party external vector database is used to store and query embeddings.
*   **Preprocessing/Deployment:**
    1.  An automated pipeline embeds all 150M+ images from the media library using the DINOv2 model.
    2.  The embeddings are loaded into the production vector database.
    3.  This pipeline runs continuously to keep the index synchronized with the media library.
*   **Experiment tracking:** [NO INFO]

### 10. Features

#### 10.1. Feature categories

*   **Primary Feature:** High-dimensionality image embeddings extracted from the DINOv2 model. These vectors serve as a visual representation of each image.
*   **Metadata Features:** Image aspect ratio is used as a filter.

#### 10.2. Feature selection

The "feature selection" process was the selection of the embedding model itself. Five state-of-the-art computer vision models were evaluated qualitatively. DINOv2 was chosen because it produced the most suitable results for the primary use case (photographic replacements), preserving subject, background, and general emotion effectively.

#### 10.3. Feature store

A third-party external vector database serves as the feature store, holding the image embeddings for the entire 150M+ image library.

#### 10.4. Feature importance

[NO INFO]

### 11. Measuring results

#### 11.1. Offline evaluation methodology

The offline evaluation was a manual, qualitative process. Engineers and designers reviewed the top 3 suggestions for 200 sample images and judged their quality based on a pre-defined similarity hierarchy. This process led to the selection of DINOv2.

#### 11.2. A/B test design

An A/B test was not explicitly mentioned. Instead, "initial pilots by professional designers" were conducted. This user study compared the workflow speed of using the new replacement suggestions against using the regular search functionality.

*   **Hypothesis:** Providing automated visual similarity suggestions will be faster than manual search for finding replacement images.
*   **Result:** The pilot showed a **4.5x increase in the speed of image replacement**, validating the system's utility.

#### 11.3. Reporting format

Results were reported via qualitative examples of strong and weak replacements and the key business metric of a 4.5x speed improvement in the design workflow.

### 12. Integration and Serving

#### 12.1. API design

The system provides online inference. It is integrated into an internal tool called the **Template Assistant**. When a designer needs to replace a flagged image in a template, the tool calls the system, which returns the top 8 most similar images.

#### 12.2. Infrastructure

*   **Embedding Model:** DINOv2 is used to generate embeddings.
*   **Serving Architecture:** A third-party external vector database is used for storing embeddings and serving nearest neighbor search queries. This was chosen over an in-memory approach (using a dedicated high-RAM machine) to reduce cost and maintenance overhead. The search query includes a filter for metadata fields like aspect ratio.

#### 12.3. SLAs and fallback strategies

*   **SLAs:** No specific latency budgets (e.g., QPS, p99 latency) are mentioned.
*   **Fallback Strategy:** The system includes a clear fallback mechanism. If a user finds the suggestions to be of poor quality (especially for cartoons or symbolic imagery), they can bypass the suggestions entirely and use Canva's regular search functionality to find a replacement manually.

#### 12.4. Release cycle

[NO INFO]

### 13. Monitoring

#### 13.1. Data quality and schema checks

The system must stay "up-to-date with changes in our media library," which implies a monitoring component to ensure the freshness and completeness of the data being indexed in the vector database.

#### 13.2. Model quality and prediction drift

The system is designed as a human-in-the-loop tool. The final selection is made by a human designer, which provides a constant, implicit form of quality monitoring. No automated monitoring for model or prediction drift is mentioned.

#### 13.3. Input/target drift detection

[NO INFO]

#### 13.4. Engineering metrics

Cost and maintenance effort were mentioned as key drivers for architectural decisions, implying they are tracked. However, no specific monitoring of metrics like latency, error rates, or cost is described.

### 14. Operations

#### 14.1. Retraining cadence

The system uses a pre-trained DINOv2 model with no fine-tuning. Therefore, there is no model retraining cadence. The operational task is to re-embed new or updated images and keep the vector database index current.

#### 14.2. Incident response and rollback procedures

The primary incident response is the user-facing fallback mechanism: designers can ignore the suggestions and use the standard search functionality if the results are unsatisfactory.

#### 14.3. Human-in-the-loop

The system is fundamentally a human-in-the-loop process for quality control.
1.  The model automatically suggests the top 8 similar images.
2.  A professional designer reviews these suggestions and selects the best fit.
3.  The designer forwards the updated design for a final human review before it is republished to the template library.