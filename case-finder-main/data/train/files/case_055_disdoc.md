- Company: Dropbox
- Title: Is this a date? Using ML to identify date formats in file names
- Technology area: Predictive ML
- Source URL: https://dropbox.tech/machine-learning/using-ml-to-identify-date-formats-in-file-names
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The system is designed to support Dropbox's "naming conventions" feature. This feature allows users to define rules for how files uploaded to a specific folder are automatically renamed. A key part of this feature is the ability to detect a date within an existing filename and use that date when applying the new naming convention.

The problem is to accurately identify date components (year, month, day) from unstructured text in filenames.

#### 1.2. Relevance & reasons

Consistent file naming is crucial for team collaboration, organization, and efficient information retrieval. However, users employ a wide and inconsistent variety of date formats, making automated detection difficult. Challenges include:
- **Format variation:** `MM/DD/YYYY`, `DD/MM/YYYY`, `YYYY-MM-DD`.
- **Abbreviations:** `Jan` for January, `FY2023` for fiscal year 2023.
- **No separators:** Dates embedded directly in names, like `survey20230601`.

A previous rule-based approach failed because the number of date formats at Dropbox's scale was too large to maintain effectively. An ML model was developed to overcome these challenges.

#### 1.3. Expectations

The system must provide granular identification of individual date components (year, month, day), not just identify a date as a single entity. This granularity is critical for downstream tasks within the naming conventions feature, such as manipulating the month separately from the day. The system must also operate with low latency to ensure a good user experience during file uploads.

#### 1.4. Previous work

An initial rule-based approach was attempted to identify dates. This was abandoned because it was too difficult to create and maintain rules for the vast range of date formats used by Dropbox users.

#### 1.5. Usage volumes and patterns

The feature is high-volume. In its first few weeks after launch, the naming conventions feature was applied to over one million files.

### 2. Goals and anti-goals

#### 2.1. Goals

- **Accuracy:** Accurately identify date components (year, month, day) from a wide variety of formats in filenames.
- **Granularity:** Decompose dates into their individual components (year, month, day) to enable flexible downstream manipulation.
- **Performance:** Achieve low real-time inference latency to provide a responsive user experience.
- **Coverage:** Handle inconsistent, ambiguous, and novel date formats.

#### 2.2. Anti-goals

- **Holistic Date Identification:** The system should not treat a date as a single, indivisible entity. This approach was rejected because it lacked the necessary granularity for downstream tasks.
- **General Entity Recognition:** The current scope is limited to extracting date components only. The model is not designed to identify other entities like names, locations, or organizational entities, although this is a potential future enhancement.

### 3. Risks and constraints

- **Performance Risk:** The initial model had a real-time latency of over one second, which was deemed a poor user experience. This required significant optimization efforts.
- **Data Coverage Risk:** The model's accuracy is dependent on the diversity of date formats in the training data. If the model encounters an unseen format, it may fail to identify the date components correctly.
- **Annotation Cost:** The size of the high-quality, human-annotated dataset was limited by the cost and effort of manual labeling. This necessitated the use of transfer learning and data synthesis.
- **Overfitting Risk:** Using synthesized data to augment the training set introduces a risk of the model overfitting to the generated patterns. This was mitigated by integrating synthesized data with the original human-annotated data.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

[NO INFO]

#### 4.2. Online/business metrics

- **Renamed Files Rate:** The primary success metric was the increase in files successfully renamed by the feature. The ML model achieved a 40% increase in renamed files over the rule-based baseline.
- **Weekly Active Users (WAU):** An increase in the feature's WAU was observed post-launch.
- **Total Renamed Files:** The total volume of files processed by the feature. Over one million files were renamed in the first few weeks.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

- **Primary Data:** File names sampled from Dropbox employees' files.
- **Synthetic Data:** A custom tool was built to generate synthesized filenames with specific date formats to augment the training set.

#### 5.2. Labeling strategy

The problem is framed as a sequence tagging task.
- **Annotation Tool:** Doccano, an open-source annotation tool, was used for manual labeling.
- **Process:** Dropbox employees reviewed sampled filenames and marked the character positions of date components (year, month, day). The process was iterative to ensure high quality.
- **Tagging Format:** The Inside-Outside-Beginning (IOB) tagging scheme was used to label tokens. Each token is labeled as `B-<ENTITY>` (Beginning), `I-<ENTITY>` (Inside), or `O` (Outside). For example, for `2022-04-01`, the tokens corresponding to `2022` would be labeled `B-YEAR`, `I-YEAR`, `I-YEAR`, `I-YEAR`. These IOB tags serve as the target labels for the classifier.

#### 5.3. Data quality and cleaning/enrichment

- **Iterative Refinement:** The manual annotation process was iterative to handle subjective or complex cases and improve dataset quality.
- **Data Synthesis:** To improve coverage for date formats not present in the initial annotated set (e.g., `MM_DD_YYYY`), a data synthesis tool was created. After annotating a few examples of a missed format, the tool generated a large set of synthetic filenames containing that format.
- **Dataset Size:** The final training set consists of "a few thousand" samples, combining both human-annotated and synthesized data.

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

[NO INFO]

### 7. Baseline solution

The baseline was a rule-based system designed to identify dates in filenames. It was chosen for its simplicity but ultimately proved inadequate. It struggled to recognize the wide variety of inconsistent and ambiguous date formats used at Dropbox's scale without extensive, hard-coded prior knowledge. The ML model was evaluated against this baseline and demonstrated a 40% improvement in the number of renamed files.

### 8. Errors and their analysis

- **Model Errors (Coverage Gaps):** The primary source of error was the model's inability to predict date components for formats not seen during training. For example, the model initially failed on the `MM_DD_YYYY` format because it was not in the training data.
- **Error Mitigation:** The operational workflow to address these errors involves:
    1. Identifying a missed format.
    2. Manually annotating a few examples of that format.
    3. Using a synthesis tool to generate a large set of new training samples with that format.
    4. Retraining the model with the augmented dataset.
- **Performance Errors (Latency):** The initial transformer-based model had an inference latency of over one second, which was unacceptable. This was addressed through model optimization techniques like pruning and quantization.

### 9. Training pipelines

The training process is a supervised learning workflow for multi-class token classification. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_055/img_005.webp`)

#### 9.1. Tooling

- **Annotation:** Doccano
- **Tokenization:** SentencePiece
- **Model:** DistilRoberta (from the Hugging Face Transformers library [inferred])
- **Data Synthesis:** A custom internal tool.

#### 9.2. Pipeline architecture

1.  **Annotation:** Filenames are manually annotated to identify date components.
2.  **Tokenization:** Filenames are divided into subword tokens using the SentencePiece tokenizer. This approach was chosen over word or character tokenization as it provides a good balance of granularity, vocabulary size, and handling of out-of-vocabulary words. It treats digits as separate tokens, which is beneficial for date parsing.
3.  **Label Generation:** Based on the manual annotations, each token is assigned an IOB tag (e.g., `B-YEAR`, `I-MONTH`, `O`) which becomes the ground truth label.
4.  **Model Training:** A DistilRoberta model is fine-tuned on the tokenized filenames and their corresponding IOB tags. It is trained as a multi-class classifier to predict the IOB tag for each input token. Transfer learning from the pre-trained DistilRoberta allows for good performance with a relatively small training set ("a few thousand samples").
5.  **Model Optimization:** To reduce inference latency, two techniques were applied:
    - **Model Pruning:** The last two encoding layers of the DistilRoberta model were removed. This reduced latency by over 30% without compromising performance. The original model has 6 layers and 88M parameters.
    - **Model Quantization:** The model's weights were converted to a lower precision format (e.g., from float32 to float16).

### 10. Features

The system uses the raw filename as input, and features are learned contextually by the transformer model.

- **Input:** Raw filename string.
- **Preprocessing:** The SentencePiece tokenizer converts the string into a sequence of subword tokens. This is the primary feature engineering step. The choice of a subword tokenizer was deliberate to capture subword-level information, providing fine granularity for digits in dates while maintaining meaningful representations for other words.
- **Learned Features:** The DistilRoberta model uses its self-attention mechanism to create rich, contextualized embeddings for each token. This approach captures word order and context, which is a significant advantage over traditional methods like TF-IDF or bag-of-words that were considered and dismissed.

### 11. Measuring results

#### 11.1. Offline evaluation

The article states that model pruning was performed "without compromising performance," but does not specify the offline evaluation metrics (e.g., F1-score, precision, recall) used to validate this.

#### 11.2. A/B testing

The ML model's performance was directly compared to the previous rule-based baseline. The ML model led to a 40% increase in the number of files successfully renamed.

#### 11.3. Reporting

Key results reported after the public launch in August 2022 include:
- A significant increase in the feature's weekly active users.
- Over one million files were renamed by the feature in its first few weeks of availability.

### 12. Integration and Serving

#### 12.1. API design

The model is integrated into the "naming conventions" feature and performs real-time inference. When a file is uploaded to a folder with an active naming convention rule, the system calls the model to analyze the filename for date components.

#### 12.2. Infrastructure

- **Model:** A pruned and quantized version of DistilRoberta.
- **Serving:** The model is served for real-time predictions.

#### 12.3. SLAs and fallback strategies

- **Latency:** A key service-level objective. The initial latency of over 1 second was too high. Optimizations brought the latency down to an "acceptable level."
    - Model pruning (removing 2 of 6 encoder layers) reduced latency by over 30%.
    - Model quantization was also applied.
- **Fallback:** [NO INFO]

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Retraining cadence

The system has a process for iterative improvement. When a date format is identified that the model handles poorly, a retraining loop is initiated: new samples are annotated, synthetic data is generated, and the model is retrained with the augmented dataset. The specific cadence (e.g., weekly, quarterly) is not mentioned.

#### 14.2. Incident response

[NO INFO]

#### 14.3. Future work

- **Improving User Onboarding:** To address user reluctance to manually configure rules, the team began work on automatically suggesting naming conventions based on the existing files in a folder.
- **Expanding Entity Recognition:** The team envisions using more sophisticated models, such as Large Language Models (LLMs), to identify a broader range of entities beyond dates, including names, locations, and organizational entities, to enable a more detailed and precise renaming experience.