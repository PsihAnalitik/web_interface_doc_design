**Company**: Bumble
**Title**: Image detection as a service
**Technology area**: Computer Vision
**Source URL**: https://medium.com/bumble-tech/image-detection-as-a-service-9bd463f74f43
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The system was developed by the Data Science team at Bumble to serve computer vision models for internal use. The company's apps, Badoo and Bumble, have millions of registered users who upload millions of photos daily, creating a rich dataset. The goal was to create a centralized service where an image is provided as input, and information about the image's content is returned as output.

#### 1.2. Relevance & reasons

The primary purpose of this service is to support the model development lifecycle, specifically during:
*   **Prototyping phase**: To quickly test and iterate on new computer vision models.
*   **Exploratory analysis**: To derive insights from the vast image dataset.
*   **Ad-hoc insights**: To deliver timely information about image content to the business.

A key business driver is to assess the potential impact of new models before committing significant resources to productionize them. For example, an insight derived from the service was that users wearing sunglasses in all their photos tend to receive fewer likes. This allows the company to provide actionable tips to users on how to improve their profiles.

#### 1.3. Expectations

The service is expected to be accessible and usable by members of the Data Science team and other stakeholders across the business. It needs to scale beyond a local machine to handle a larger volume of images for analysis and prototyping. The interface should be simple, allowing users without domain-specific knowledge of Python or the underlying models to interact with it.

#### 1.4. Previous work

The team considered using third-party machine vision APIs, such as Google Cloud Vision and AWS Rekognition. However, they decided against this approach for two main reasons:
1.  **Cost**: To minimize operational expenses.
2.  **Data Privacy**: To keep user data in-house.

The alternative to the service was running models on a local machine, which was not scalable enough for their needs.

#### 1.5. Usage volumes and patterns

The underlying data comes from millions of users on Badoo and Bumble, who upload millions of photos per day. The service itself is not directly serving production traffic but is used internally for analysis and prototyping, which requires scoring a significant number of images to assess potential business impact.

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Provide a unified service**: Create a single, centralized service for image content analysis accessible to the Data Science team and other business units.
*   **Support model evaluation**: Enable the team to assess the potential business impact of new computer vision models before they are fully productionized.
*   **Enable rapid prototyping and analysis**: Facilitate exploratory work, ad-hoc analysis, and rapid model prototyping.
*   **Ensure cross-language compatibility**: Use a REST API to allow applications written in different languages to easily consume the models.
*   **Maintain simplicity and flexibility**: The framework should be simple, lightweight, and easy to get started with.

#### 2.2. Anti-goals

*   **Avoid third-party dependencies**: The system should not rely on external vision APIs like Google Cloud Vision or AWS Rekognition.
*   **Avoid heavy frameworks**: The implementation should avoid complex, heavy web frameworks like Django in favor of a simpler microframework (Flask).

### 3. Risks and constraints

*   **Cost**: A primary constraint was the desire to minimize costs, which drove the decision to build an in-house solution.
*   **Data Privacy**: A strict constraint was to keep all user data and images within the company's infrastructure.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

[NO INFO]

#### 4.2. Online/business metrics

The service is used to generate insights that correlate with business metrics. The example provided is the observation that users with sunglasses in all their pictures receive "fewer likes." This suggests that user engagement metrics like "likes" are used to evaluate the real-world impact of image characteristics identified by the models.

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The data consists of user-uploaded photos from the Badoo and Bumble applications. The platform receives millions of new photos each day.

#### 5.2. Labeling strategy

[NO INFO]

#### 5.3. Available metadata

[NO INFO]

#### 5.4. Data quality issues and cleaning

[NO INFO]

#### 5.5. ETL

[NO INFO]

### 6. Validation schema

[NO INFO]

### 7. Baseline solution

The baseline solution before this service was running models on a local machine, which was not scalable for larger analyses. The service itself acts as a framework to evaluate new models against business needs before they are considered for full production deployment. The alternative to building the service in-house was using third-party APIs (e.g., Google Cloud Vision), which was rejected due to cost and data privacy concerns.

### 8. Errors and their analysis

[NO INFO]

### 9. Training pipelines

#### 9.1. Tooling

*   **Training Environment**: Models were initially trained using Jupyter notebooks and `.py` scripts.
*   **Libraries**: The article mentions `load_model`, suggesting a framework like Keras/TensorFlow. NumPy is used for data manipulation.

#### 9.2. Preprocessing, training, evaluation, and deployment automation

*   **Training**: The article does not detail the training process, only that pre-trained models (`.h5` files) are loaded by the service.
*   **Inference Preprocessing**: For prediction, images are processed as follows:
    1.  Load the image with a specific target size (`target_size=(img_width, img_height)`).
    2.  Convert the image to a NumPy array (`image.img_to_array`).
    3.  Expand the tensor dimensions to create a batch of one (`np.expand_dims`).
    4.  Normalize pixel values by dividing by 255.
*   **Deployment**: The service is packaged in a Docker container for deployment.

#### 9.3. Experiment tracking

[NO INFO]

### 10. Features

The service provides several types of "features" or predictions about image content, served by different models.

*   **Image Classification**:
    *   Predicts binary attributes of the person in the image.
    *   Examples: `smiling`, `wearing sunglasses`.
    *   Output: A probability score for each attribute.
*   **Textual Descriptions**:
    *   Generates a natural language sentence describing the image content.
    *   Model Architecture: A combination of a CNN and an LSTM.
*   **Object Detection**:
    *   Detects objects present in an image.
    *   Model: An off-the-shelf YOLO model from a GitHub repository.

### 11. Measuring results

#### 11.1. Offline evaluation

[NO INFO]

#### 11.2. A/B test design

The service is used in a pre-A/B testing phase called "potential impact analyses." This involves using the models to score large sets of images and correlating the outputs with business metrics (e.g., likes) to estimate the value a project might deliver if it were fully productionized. This analysis helps decide whether to allocate resources for a full production launch and A/B testing.

#### 11.3. Reporting format

The service's API returns a JSON object containing the prediction probabilities. For example:
`{'prob_smiling': 0.11, 'prob_sunglasses': 0.20}`

These results are used in ad-hoc analyses and reports for business stakeholders.

### 12. Integration and Serving

#### 12.1. API design

*   **Protocol**: REST API over HTTP.
*   **Framework**: Python Flask with the Flask-RESTful extension.
*   **Endpoint**: A single endpoint `/` accepts `POST` and `PUT` requests.
*   **Request Format**: Images are sent as files in a multipart form request (e.g., `curl -F file=@'...'`).
*   **Response Format**: A JSON object containing probabilities for the requested features.
*   **Model Loading**: Pre-trained models (e.g., `smiling.h5`, `sunglasses.h5`) are loaded into memory when the Flask server starts.

#### 12.2. Infrastructure

*   **Web Framework**: Flask was chosen over Django for its simplicity and flexibility.
*   **Hosting**: The service is hosted on internal company servers.
*   **Hardware**: The servers are equipped with GPUs to accelerate model inference computation time.
*   **Containerization**: The application is packaged into a Docker container. The service is started by executing into the running container (`docker exec -it <container_id> bash`) and running the Python script (`python server.py`).

#### 12.3. SLAs, latency budgets, and fallback strategies

The article mentions that response times can be reviewed from a Jupyter notebook but does not specify any formal SLAs, latency budgets, or fallback mechanisms.

#### 12.4. Release cycle

[NO INFO]

### 13. Monitoring

The article mentions making requests to the server and reviewing response times from a Jupyter notebook, but no automated monitoring for data quality, model quality, or system metrics is described.

### 14. Operations

#### 14.1. Day-to-day operational procedures

The service is primarily used by the Data Science team for:
*   Exploratory data analysis.
*   Ad-hoc analysis for business requests.
*   Prototyping new computer vision models.

Other people in the business can also access the service, for example, by making requests from a Jupyter notebook.

#### 14.2. Retraining cadence

[NO INFO]

#### 14.3. Incident response and rollback procedures

[NO INFO]