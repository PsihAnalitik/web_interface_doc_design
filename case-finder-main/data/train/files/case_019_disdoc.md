**Company**: Yelp
**Title**: Yelp Content As Embeddings
**Technology area**: CV
**Source URL**: https://engineeringblog.yelp.com/2023/04/yelp-content-as-embeddings.html
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

Yelp's primary goal is to provide users with easily accessible, high-quality content. To achieve this, content such as reviews, business information, and photos must be effectively tagged, organized, and ranked. The Content and Contributor Intelligence team initiated a project to create general-purpose, low-dimensional representations (embeddings) of this content.

The core problem is to transform Yelp's massive and diverse content (text, images, business metadata) into a semantically meaningful vector format that can be used across various unspecified machine learning tasks.

#### 1.2. Relevance & reasons

Having readily available embeddings that encapsulate semantic information for Yelp's vast datasets simplifies and accelerates the development of new deep learning models. These embeddings can serve as a high-quality baseline for any model's input features, improving usability and efficiency for internal engineering teams.

Specific applications for these embeddings include:
*   Tagging and information extraction
*   Sentiment analysis
*   Ranking content for relevance and information diversity
*   Generating similarity-based recommendations (e.g., "Users like you also liked...")

#### 1.3. Expectations

The system is expected to produce "universal" embeddings that are versatile enough to be applied to a wide range of tasks without needing to be retrained for each specific use case. The resulting embeddings should be stored in a central database, making them accessible and easy to use for any internal project at Yelp.

#### 1.4. Previous work

Prior to this unified embedding project, Yelp had existing models for specific tasks, which served as baselines for comparison:
*   Three separate **ResNet50** classification models were in production for photo categorization:
    *   A 5-way Restaurant, Food, and Nightlife classifier.
    *   A 27-class food dish classifier.
    *   A 5-class Home Services Contractor classifier.

#### 1.5. Usage volumes and patterns

The system is designed to handle the massive scale of Yelp's data, resulting in a database containing "hundreds of millions of embeddings." These embeddings are consumed by many internal teams to improve their products.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Generate Universal Embeddings:** Create low-dimensional, semantic representations for review text, business information, and photos.
*   **Versatility:** The embeddings must be applicable to a wide variety of downstream tasks, including tagging, information extraction, sentiment analysis, and ranking.
*   **Improve Development Efficiency:** Provide a strong, pre-computed feature baseline to accelerate the implementation of new deep learning models.
*   **Centralized Accessibility:** Store all embeddings in a unified system that is easy for any internal team to access and use.
*   **Content Understanding:** Capture the essence, context, and sentiment from Yelp's most valuable content, particularly user reviews.

#### 2.2. Anti-goals

*   **Task-Specific Optimization:** The system is not intended to create embeddings that are hyper-optimized for a single task at the expense of generalizability. The goal is universality.
*   **Generative Models:** The text embedding models are not generative; they are designed for representation learning to be used in supervised tasks.

### 3. Risks and constraints

*   **Model Vulnerabilities (CLIP):**
    *   **Typographical Attacks:** The CLIP model is susceptible to being fooled by text within an image. For example, a photo of an apple with a handwritten "iPod" sticker could be misclassified as an iPod. This is a risk for Yelp photos that may contain restaurant merchandise or menus with prominent text.
    *   **Foreground Bias:** The model's attention mechanism can over-emphasize foreground elements (like people) at the expense of the background, leading to misclassification of scenes like restaurant interiors or exteriors.
*   **Domain Adaptation Failure:** An initial hypothesis was that a model fine-tuned on Yelp's domain-specific text would outperform a general model. However, experiments showed this was not the case for the text encoder, possibly because the general model's training data was already diverse enough or the fine-tuning tasks were not sufficiently varied.
*   **Label Ambiguity:** The quality of evaluation depends on the ground-truth labels. Some dataset labels were found to be ambiguous or less descriptive than the model's predictions (e.g., an image of "Fried Chicken and Waffles" labeled only as "Waffles").
*   **Data Scale:** The system must be able to process and store embeddings for hundreds of millions of content pieces.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Classification Metrics:** **Precision** and **Recall** are used to evaluate the performance of photo classification models (CLIP vs. ResNet50) on several benchmark tasks. Confusion matrices are also used for error analysis.
*   **Semantic Similarity:** **Cosine similarity** is used to validate text embeddings. A heatmap of cosine similarities between review embeddings was generated to verify that reviews from the same business category are closer in the vector space than reviews from different categories. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_019/img_003.png`)

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

*   **Photo Embeddings (CLIP):** The model uses **contrastive representation learning**. It aims to maximize the cosine similarity of correct image-text pairs while minimizing the similarity of incorrect pairs in a batch.
*   **Text Embeddings (USE):** The source mentions the model was trained on a variety of tasks (classification, similarity, clustering), but does not specify the exact loss functions used.

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Text:** User-generated reviews, photo captions, user search queries, and survey responses.
*   **Images:** Photos uploaded by users and businesses.
*   **Business Metadata:** Information associated with business profiles on Yelp.

#### 5.2. Labeling strategy or proxy labels

For model evaluation and fine-tuning, several supervised datasets with human-provided labels were used:
*   **Text Model Fine-Tuning Tasks:**
    *   Review Category Prediction
    *   Review Rating Prediction
    *   Search Category Prediction
*   **Photo Model Evaluation Tasks:**
    *   **5-Way Restaurant Classifier:** Photos hand-labeled as `Food`, `Drink`, `Menu`, `Interior`, or `Exterior`.
    *   **Food Classifier:** Photos hand-labeled with one of 27 food dish categories.
    *   **Home Services Contractor Classifier:** Photos hand-labeled with one of 5 repair categories (e.g., `Bathroom, Bathtub and Shower`, `Kitchen`).

#### 5.3. Data quality issues and cleaning/enrichment

*   **Label Engineering:** For the CLIP model, class labels required manual engineering to be effective. For example, the label `Interior` was changed to the prompt `A photo of inside a restaurant`.
*   **Ambiguous Labels:** Some ground-truth labels were found to be incomplete. For instance, an image of "Fried Chicken and Waffles" was labeled only as `Waffles`, leading CLIP to make a seemingly incorrect but contextually more accurate prediction.
*   **Subject Mismatch:** Some images were labeled based on a minor element. For example, an image labeled `Grilled Fish` was primarily a salad, causing CLIP to classify it as `Salad`.

### 6. Validation schema

#### 6.1. Train/validation/test split strategy

[NO INFO]

#### 6.2. Evaluation framework

The primary validation strategy was to compare the performance of new embedding-based models against existing, specialized production models on a set of predefined classification tasks.

*   **Text Embedding Validation:**
    *   A Yelp-fine-tuned USE model was compared against the off-the-shelf pre-trained USE model.
    *   Evaluation tasks included: Photo Caption Classification, Menu Item Classification, Business Property Classification, and Synonym Generation.
*   **Photo Embedding Validation:**
    *   The zero-shot OpenAI CLIP model was compared against three production ResNet50 classifiers.
    *   The comparison was performed on three tasks: 5-Way Restaurant Classifier, 27-class Food Classifier, and 5-class Home Services Contractor Classifier.
    *   Performance was measured using precision and recall for each class.

### 7. Baseline solution

*   **Text Embeddings:** The baseline was the off-the-shelf **Universal Sentence Encoder (USE)** model from TensorFlow-Hub. An experiment to create a superior, Yelp-fine-tuned encoder was conducted, but it failed to outperform this baseline.
*   **Photo Classification:** The baselines were three existing **ResNet50** models, each trained on Yelp data for a specific classification task (restaurant scenes, food dishes, home services). These were compared against the new zero-shot CLIP-based approach.

### 8. Errors and their analysis

*   **Text Model (USE):** The attempt to fine-tune the USE model on Yelp-specific tasks (Review Category Prediction, Rating Prediction, etc.) did not yield a better model than the pre-trained, off-the-shelf version. The conclusion was that either the Yelp domain is general enough to be well-covered by USE's original training, or the fine-tuning experiments lacked sufficient task diversity.

*   **Photo Model (CLIP):**
    *   **Prompt Engineering Requirement:** Naive class labels (e.g., `Menu`) perform poorly. Engineered prompts (e.g., `A photo of a menu`) are necessary and significantly impact performance, though their effectiveness varies by class. For the `Menu` class, CLIP's recall was high (94%) but precision was low (51%), indicating it identified most menus but also misclassified many other things as menus.
    *   **Foreground Bias:** CLIP misclassified many `Interior` and `Exterior` photos as `Other` because it focused on people in the foreground rather than the background scene.
    *   **Multi-Concept Images:** CLIP's predictions can be more nuanced than the single-label dataset. It correctly identified "Chicken Wings & Fried Chicken" (44% probability) in an image labeled only as `Waffles` (11% probability).
    *   **Precision/Recall Trade-off:** For the Home Services classifier, introducing a 70% confidence threshold for a prediction improved precision but lowered recall across most categories. For example, precision for `Decks and Railing` increased from 20% to 35%, while recall dropped from 84% to 76%.

### 9. Training pipelines

#### 9.1. Tooling

*   **Text Embeddings:** **TensorFlow-Hub** for accessing the pre-trained Universal Sentence Encoder (USE) model.
*   **Photo Embeddings:** **HuggingFace** for accessing the pre-trained OpenAI CLIP model.

#### 9.2. Pipeline stages

The overall project consisted of:
1.  **Model Selection & Experimentation:** Evaluating off-the-shelf models (USE, CLIP) and attempts at fine-tuning (USE).
2.  **Embedding Generation:** A large-scale batch process to generate embeddings for all relevant Yelp content (reviews, photos).
3.  **Storage:** Storing the hundreds of millions of generated embeddings in a new, centralized database system to make them accessible for internal teams.

#### 9.3. Experiment tracking and CI/CD

[NO INFO]

### 10. Features

The primary output of this system is the embeddings themselves, which serve as features for downstream models.

*   **Review Text Embeddings:**
    *   **Model:** Universal Sentence Encoder (USE), specifically the Deep Averaging Network (DAN) version.
    *   **Architecture:** The model averages word and bigram embeddings, then passes the result through a deep neural network to produce a fixed-length 512-dimension vector. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_019/img_002.png`)
    *   **Source:** Yelp review text.

*   **Photo Embeddings:**
    *   **Model:** OpenAI's Contrastive Language-Image Pre-training (CLIP) model, used in a zero-shot fashion.
    *   **Architecture:** Uses an image encoder to generate photo embeddings. These embeddings exist in a shared vector space with text embeddings from a corresponding text encoder.
    *   **Source:** Yelp photos.

*   **Business Embeddings:**
    *   **Method:** This is a composite embedding created by averaging the text embeddings of the 50 most recent reviews for a given business.
    *   **Source:** Review text embeddings.
    *   **Future Work:** The plan is to incorporate photo embeddings and other business metadata into this representation.

### 11. Measuring results

#### 11.1. Offline evaluation

*   **Text Embeddings:** A qualitative evaluation was performed using a cosine similarity heatmap on a sample of 44 reviews across 4 business categories (Restaurants, Dry Cleaning, Groomer, Plastic Surgeon). The heatmap confirmed that reviews from the same category had higher similarity scores (were closer in the vector space).
*   **Photo Embeddings:** A quantitative evaluation was performed by comparing the zero-shot CLIP model against production ResNet50 models on three classification tasks. Results were reported in tables comparing precision and recall for each class. For example, on the 5-way classifier, CLIP achieved 91% recall for `Drink` vs. ResNet50's 87.1%, but 77% recall for `Interior` vs. ResNet50's 92.2%.

#### 11.2. A/B test design

[NO INFO]

#### 11.3. Reporting format and decision criteria

Results are presented in tables comparing precision and recall side-by-side for the baseline (ResNet50) and the new model (CLIP). The decision to adopt a model is based on its potential and performance on these offline tasks. For example, despite some weaknesses, CLIP's strong zero-shot performance encouraged further exploration and plans for fine-tuning.

### 12. Integration and Serving

#### 12.1. API design, batch vs. online serving

The system follows a **batch processing** pattern. Embeddings are pre-computed for the entire corpus of Yelp content and stored in a database. Downstream applications query this database to retrieve embeddings for use in their own models or business logic. This is not a real-time embedding generation service.

#### 12.2. Infrastructure

The primary infrastructure component is a database designed to store and serve "hundreds of millions of embeddings."

#### 12.3. SLAs, latency budgets, and fallback strategies

[NO INFO]

#### 12.4. Use cases

The generated embeddings are already being used by many teams at Yelp to power various products:
*   **Similarity and Recommendations:**
    *   Business-to-business similarity ("Since you like business A, you might like business B").
    *   User-to-business recommendations.
    *   User-to-user similarity for recommendations ("Users like you also liked...").
*   **Photo Search and Tagging:** Using CLIP embeddings to better identify and tag photo categories, especially for unseen or long-tail categories, to improve photo search.

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Day-to-day operational procedures

[NO INFO]

#### 14.2. Retraining cadence and ownership

*   **Business Embeddings:** The business embedding is calculated from the "50 most recent reviews," which implies a recurring update process to keep the embeddings fresh as new reviews are posted.
*   **Future Work / Iteration:** The team is actively working on improving the embeddings. Current explorations include:
    *   Fine-tuning the CLIP model on the Yelp domain to improve photo embeddings.
    *   Enhancing the business embedding by incorporating photo embeddings and other business metadata.

#### 14.3. Incident response and rollback procedures

[NO INFO]