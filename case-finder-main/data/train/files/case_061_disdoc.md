**Company**: Scribd
**Title**: Identifying Document Types at Scribd
**Technology area**: Computer Vision
**Source URL**: https://tech.scribd.com/blog/2021/identifying-document-types.html
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The core of Scribd's business involves a large and diverse corpus of user-uploaded documents. To improve discovery and recommendations, the Applied Research team initiated a project to extract key document metadata. This document describes the first stage of that system: classifying arbitrary user-uploaded documents based on their visual structure. The problem is analogous to how a human can perform a "first glance" to distinguish a comic book from a business report without reading the text.

#### 1.2. Relevance & reasons

Understanding the composition of the document corpus unlocks new opportunities for downstream systems, particularly for discovery and recommendation. As the corpus has grown over the years, its diversity has made manual or simple heuristic-based understanding an increasing challenge. This ML system is designed to provide a foundational layer of metadata (document type) for a multi-component document understanding system.

#### 1.3. Expectations

The primary expectation is for a model that can classify documents based on visual cues alone, making it language-agnostic and applicable to the entire corpus, which includes everything from math homework to Philippine law and engineering schematics. The output of this model will be used to route documents to more specialized, type-specific information extraction models.

#### 1.4. Previous work

This system is presented as the first part of a new, comprehensive document understanding system. The prior state was a lack of structured understanding of the document corpus.

#### 1.5. Usage volumes and patterns

The system must be capable of running on Scribd's entire document corpus, which consists of "hundreds of millions of documents".

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Classify documents by visual type**: The system must classify documents into a set of predefined categories based on visual layout and structure.
*   **Language-agnostic**: The model must work for documents in any language, as it relies on visual cues rather than text content.
*   **High throughput and low cost**: The model must have a low inference time to be economically viable for processing hundreds of millions of documents.
*   **Enable downstream processing**: The classification output is intended to be used by subsequent, more specialized ML models (e.g., information extraction for text-heavy documents).

#### 2.2. Anti-goals

*   **Semantic understanding**: The system is not intended to understand the topic or content of the document (e.g., distinguishing fiction from non-fiction). This is deferred to downstream models.
*   **Text-based classification**: The model should not rely on reading or understanding the text within the document.
*   **Maximizing accuracy at all costs**: Models with the highest academic accuracy (e.g., EfficientNet) were not chosen because their inference time and training complexity were too high for the required scale. A balance between accuracy and efficiency is required.

### 3. Risks and constraints

*   **Data diversity**: The corpus is extremely heterogeneous in content, language, and structure, making it difficult to define a comprehensive set of classes.
*   **Mixed-type documents**: A single document can contain pages of different types (e.g., text-heavy pages and pages with tables), which complicates the labeling process for training a page-level classifier.
*   **Model overconfidence**: The model was found to produce overconfident (>99%) but incorrect predictions, rendering simple confidence thresholding ineffective for improving precision.
*   **Incorrect inductive biases**: The model is at risk of learning simplistic and incorrect visual heuristics (e.g., assuming any page with many horizontal lines is sheet music).
*   **Scale and cost**: The sheer volume of documents (hundreds of millions) imposes a strict constraint on inference time and computational cost.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Accuracy vs. Inference Time**: This was the key trade-off used for model selection. SqueezeNet was chosen for providing the best balance.
*   **Precision**: Mentioned as a target for improvement. For classes that suffered from low precision, dedicated binary classifiers were built.

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The data source is the corpus of user-uploaded documents on the Scribd platform.

#### 5.2. Class definition and labeling

The document types were defined using a two-pronged approach:
1.  **Expert knowledge**: Consulting with subject matter experts at Scribd to understand the kinds of documents they have encountered.
2.  **Data-driven exploration**: Creating embeddings for documents based on user behavior/usage, then clustering and visualizing these embeddings to identify structurally similar document groups. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_061/img_002.png`)

This process led to the definition of 6 main classes, including `sheet-music`, `text-heavy`, `comics`, and `tables`. An explicit `other` class was also added to handle out-of-distribution examples.

#### 5.3. Labeling strategy

Since document-level labels are inappropriate for training a page classifier (due to mixed-type documents), an active learning approach was used to gather page-level labels:
1.  A small set of pages for each class was hand-labeled.
2.  Binary classifiers were trained iteratively for each class.
3.  At each iteration, the model's most and least confident predictions were reviewed to understand its inductive biases.
4.  The training set was supplemented with new examples to correct these biases (e.g., adding non-sheet-music pages with horizontal lines to prevent misclassification).
5.  This process resulted in a large set of reliable page labels and a set of binary classifiers that could be used for further data gathering.

#### 5.4. Data quality issues

*   **Label noise from mixed-type documents**: A document labeled "text-heavy" might contain pages with tables or images, which would pollute the training data if page labels were naively inherited from the document label.
*   **Out-of-distribution (OOD) examples**: The corpus contains many documents that do not fit neatly into the defined classes. These were a source of errors and were handled by adding them to a dedicated "other" class during training.

### 6. Validation schema

#### 6.1. Train/validation/test split

The article mentions using "training and testing data" but does not specify the splitting strategy.

#### 6.2. Holdout sets

Error analysis was performed on a "large sample of documents from production," which can be considered a form of holdout set evaluation.

#### 6.3. Leakage risks

[NO INFO]

### 7. Baseline solution

For the final document-level classification, a simple ensemble of page-level predictions was used as a strong baseline. This approach involved:
1.  Sampling 4 pages from a document.
2.  Classifying each page using the page-level model.
3.  Aggregating these predictions to form a document-level classification.

This simple ensemble proved to be an "extremely strong baseline" that was difficult to improve upon even when adding other document metadata (e.g., total page count, page dimensions).

### 8. Errors and their analysis

#### 8.1. Error taxonomy

*   **Overconfident misclassifications**: The model produced predictions with >99% confidence that were incorrect. This was a major issue as it made confidence-based thresholding for precision improvement ineffective.
*   **Incorrect inductive bias**: The model learned spurious correlations, such as associating any page with horizontal lines with the `sheet music` class. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_061/img_004.png`)
*   **Out-of-distribution errors**: Documents that did not belong to any of the target classes were a source of errors.

#### 8.2. Diagnostic and mitigation approaches

*   **Error analysis on production data**: A large sample of production documents was analyzed to identify patterns in misclassifications.
*   **Handling OOD examples**: An explicit `other` class was added to the model. Adversarial and OOD examples identified during error analysis were added to this class, and the model was retrained to improve its ability to reject unknown types.
*   **Class-specific models**: For classes that suffered from particularly low precision due to overconfidence issues, individual binary classifiers were built to act as a second-stage filter or replacement, improving precision for those specific types.
*   **Active learning loop**: During data gathering, the most and least confident predictions of iterative models were reviewed to identify and correct developing inductive biases by supplementing the training data.

### 9. Training pipelines

#### 9.1. Tooling

*   **Frameworks**: `PyTorch`, `fast.ai`.

#### 9.2. Architecture and training process

*   **Model Architecture**: `SqueezeNet` was chosen after experiments with other architectures like `EfficientNet`, `ResNets`, and `DenseNets`. SqueezeNet offered the best balance of accuracy and inference time, which was critical for the project's scale. Its small size allowed for fine-tuning the entire model rather than just using it as a fixed feature extractor.
*   **Training Method**: Transfer learning was used, starting with a pre-trained ImageNet model and fine-tuning it on the document page classification task.
*   **Data Gathering**: An active learning process with iterative binary classifiers was used to build the labeled dataset.

#### 9.3. Experiment tracking

[NO INFO]

#### 9.4. CI/CD

[NO INFO]

### 10. Features

#### 10.1. Feature categories

*   **Visual Features**: The primary features are learned directly from the pixels of the document pages by the `SqueezeNet` computer vision model.
*   **Metadata Features (Considered but not used)**: Additional metadata such as `total page count` and `page dimensions` were experimented with for the document-level classification step but were found to not provide significant improvement over the baseline page-prediction ensemble.

### 11. Measuring results

#### 11.1. Offline evaluation

*   **Model comparison**: Different CNN architectures were compared based on their ImageNet accuracy and, more importantly, their performance (accuracy vs. inference time) on the page classification task. `SqueezeNet` was selected for its efficiency.
*   **Ensemble strategy evaluation**: The performance of sampling 4 pages for the document-level prediction was empirically verified against the page distribution in the corpus.

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting

[NO INFO]

### 12. Integration and Serving

#### 12.1. System architecture

The document type classifier is the first component in a larger document understanding pipeline. Its output is used to route documents to specialized downstream models. For example, documents classified as `text-heavy` are sent to a "Text Heavy Information Extraction" model. This suggests a batch processing or asynchronous workflow. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_061/img_006.png`)

#### 12.2. Serving infrastructure

*   **Processing Mode**: The system is designed for large-scale batch processing of "hundreds of millions of documents".
*   **Efficiency**: Low inference time is a key requirement, directly influencing infrastructure costs. The choice of the lightweight `SqueezeNet` model was driven by this constraint.

#### 12.3. SLAs and fallback strategies

*   **Latency**: While no specific SLA is mentioned, low inference time is a primary design goal to manage cost and throughput at scale.
*   **Fallback**: The explicit `other` class serves as a fallback mechanism, catching documents that do not fit into the predefined categories and preventing them from being routed incorrectly to downstream systems.

### 13. Monitoring

#### 13.1. Data and model quality

The process of performing "error analysis of a large sample of documents from production" serves as a manual form of model performance monitoring. No automated monitoring for data drift, prediction drift, or model degradation is mentioned.

#### 13.2. Engineering metrics

[NO INFO]

### 14. Operations

#### 14.1. Retraining

The model was retrained after augmenting the dataset with adversarial examples added to the `other` class. The active learning loop used for data collection also implies an iterative retraining process. A fixed, scheduled retraining cadence is not mentioned.

#### 14.2. Incident response

[NO INFO]

#### 14.3. Non-engineering considerations

The definition of document types was a collaborative process involving "subject matter experts" at Scribd, ensuring the classes were relevant to the business and the corpus.