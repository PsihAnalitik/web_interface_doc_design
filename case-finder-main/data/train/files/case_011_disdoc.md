- Company: New York Times
- Title: Experimenting with Handwriting Recognition for The New York Times Crossword
- Technology area: CV
- Source URL: https://open.nytimes.com/experimenting-with-handwriting-recognition-for-new-york-times-crossword-a78e08fec08f
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The project originated as an experiment during MakerWeek 2023, The New York Times' annual hackathon. iOS and Android engineers explored adding handwriting input to The New York Times Crosswords mobile app. The goal is to allow users to write answers directly into the crossword grid using a stylus or their finger, as an alternative to the existing keyboard.

#### 1.2. Relevance & reasons

The primary motivation is to enhance the user experience of the Crosswords app. The current input method is a custom in-app software keyboard. Allowing handwriting could provide a more natural and engaging way for users to interact with the puzzle, potentially improving the experience for existing users and attracting new subscribers.

#### 1.3. Expectations

This project is an exploration for a potential future feature and has not been released. The core expectation is to create a system that can accurately recognize single, hand-written letters (A-Z) and digits (0-9) entered into individual crossword squares (both Mini and Daily puzzles) and provide a smooth, responsive user experience.

#### 1.4. Previous work

The existing system for text entry in the Crosswords app is a custom-built software keyboard. The handwriting recognition feature is being built as a new, alternative input modality.

#### 1.5. Usage volumes and patterns

[NO INFO]

### 2. Goals and anti-goals

#### 2.1. Goals

*   **Functionality**: Enable users to write single characters (letters) into crossword squares using a finger or stylus.
*   **Accuracy**: Achieve high recognition accuracy for 62 characters (26 uppercase, 26 lowercase, 10 digits). The offline model achieved ~91% validation accuracy.
*   **Performance**: Ensure a smooth and responsive user experience, avoiding a "degraded and choppy" feel. This includes intelligently determining when a user has finished writing a character.
*   **Efficiency**: The model must be small and efficient enough for on-device deployment on mobile platforms (Android and iOS). The final trained model file is approximately 100KB.

#### 2.2. Anti-goals

*   **Out-of-Scope Characters**: The system is not designed to recognize punctuation or multi-character words in a single input.
*   **Complex Cases (Initially)**: The initial version does not aim to solve for "partial letters" or "letters that are spaced at irregular intervals." These are identified as areas for future work.
*   **General OCR**: The system is not a general-purpose OCR engine; it is specialized for single-character recognition within a defined box.

### 3. Risks and constraints

*   **Technical Constraints**:
    *   **On-Device Inference**: The model must run entirely on the user's mobile device using TensorFlow Lite.
    *   **Model Size**: The compiled model must be small to minimize the impact on the app's binary size. The target was successfully met with a ~100KB `.tflite` file.
    *   **Platform Integration**: The solution must integrate with a custom UI component (`SketchBox`) on both Android and iOS.
*   **User Experience Risks**:
    *   **Input Latency**: The system must determine when a user has finished writing a character. Waiting too long feels slow, while acting too quickly leads to misinterpretation (e.g., recognizing the first stroke of a 'K' as an 'I'). An initial solution uses a 500-1000ms delay.
    *   **Recognition Accuracy**: Poor accuracy would frustrate users and make the feature unusable.
*   **Data Constraints**:
    *   **Handwriting Variability**: The model must be robust to a wide variety of handwriting styles, including differences in slant, size, and off-center placement within the square.
    *   **Device Variability**: The input capture must work across devices with different screen sizes and resolutions.

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Validation Accuracy**: The primary offline metric used was classification accuracy. The final model achieved an average validation accuracy of approximately 91% on the augmented EMNIST dataset.

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Digits (Initial Model)**: Modified National Institute of Standards and Technology (MNIST) dataset.
*   **Letters and Digits (Final Model)**: EMNIST (Extended MNIST) dataset, which includes 26 lowercase letters, 26 uppercase letters, and 10 digits, for a total of 62 character classes. The source cited is `http://arxiv.org/abs/1702.05373`.

#### 5.2. Labeling strategy

The project used pre-existing, labeled academic datasets (MNIST and EMNIST).

#### 5.3. Data quality issues and cleaning

*   **"Too Perfect" Data**: The initial model trained on the standard MNIST dataset performed poorly because the data was too clean and centered. It did not reflect real-world user input, where characters are often written off-center and with more variation.
*   **Data Preprocessing**:
    1.  **Input Capture**: A custom `SketchBox` component captures user strokes as raw pixel data from the canvas.
    2.  **Downscaling**: Raw 128x128 input images are downscaled to 28x28.
    3.  **Binarization**: Images are binarized to remove noise and simplify the input for the model.
*   **Data Augmentation**:
    *   To address the "too perfect" data issue, data augmentation was employed to generate more realistic training samples.
    *   **Techniques**: Affine transformations were applied, including minor off-center shifts, rotations, and scaling.
    *   **Scale**: The dataset was expanded from "thousands to over 1 million samples."

### 6. Validation schema

*   **Cross-Validation**: The team used **Stratified K-Fold cross-validation** to diversify training and ensure robust evaluation. This involved training on randomized subsets of the augmented training/validation data.

### 7. Baseline solution

The project followed an iterative approach, with the first model serving as a baseline.

*   **V1: Digit Recognition Model**
    *   **Architecture**: A basic Convolutional Neural Network (CNN).
    *   **Dataset**: Standard MNIST dataset for digits.
    *   **Result**: The model failed in practice. It performed poorly on real user input because the training data was "too perfect" and did not generalize to the variability of actual handwriting (e.g., off-center placement). This failure directly led to the adoption of data augmentation.

### 8. Errors and their analysis

*   **Input Timing Errors**:
    *   **Problem**: The system might process an incomplete character if it triggers recognition too quickly between strokes (e.g., interpreting the vertical stroke of a 'K' as an 'I').
    *   **Analysis/Solution**: A mutex-like input locking system was introduced, which waits for a period of 500 to 1000 milliseconds after a stroke before triggering recognition. This is a trade-off between responsiveness and accuracy.
*   **Model Generalization Errors**:
    *   **Problem**: The initial digit-recognition model failed to recognize real-world handwriting.
    *   **Analysis**: The root cause was identified as a domain mismatch between the clean, centered MNIST training data and the messy, variable user-generated input.
    *   **Solution**: This was resolved by implementing data augmentation (shifts, rotations, scaling) to create a more robust and realistic training set.
*   **Known Limitations (Future Work)**:
    *   The current model does not handle partial letters.
    *   The model does not handle letters that are spaced at irregular intervals.

### 9. Training pipelines

#### 9.1. Tooling

*   **ML Framework**: TensorFlow
*   **Mobile Deployment Framework**: TensorFlow Lite
*   **Target Platforms**: Android, iOS

#### 9.2. Training and deployment process

1.  **Model Architecture**: A Deep Convolutional Neural Network (Deep-CNN) was designed. The architecture was refined by adding more layers to increase its "power" for the more complex letter recognition task compared to just digits.
2.  **Hyperparameter Tuning**: A randomized parametric search was used to find optimal hyperparameters, which was an improvement over the previous strategy of "guessing the right parameters."
3.  **Training**: The model was trained on the augmented EMNIST dataset using Stratified K-Fold cross-validation.
4.  **Compilation**: The final trained model was compiled into a `.tflite` file, with a size of approximately 100KB.
5.  **Deployment**: The `.tflite` file was integrated into the mobile application builds.
6.  **Iteration**: The team iterated multiple times on different models and configurations to achieve a satisfactory result.

### 10. Features

*   **Input Features**: The model's input is a 28x28 binarized pixel image of the character written by the user in the `SketchBox`.
*   **Learned Features**: The Deep-CNN automatically learns a hierarchy of features from the pixel data. These include low-level features like edges and curves, and higher-level features corresponding to the geometric structures that distinguish different characters. The article uses an analogy of a network learning to identify a bird by detecting "feathers, eyes, edges of the beak."
*   **Feature Engineering**: No manual feature engineering was performed; the process relies on the CNN's feature extraction capabilities.

### 11. Measuring results

#### 11.1. Offline evaluation

*   **Methodology**: The model was evaluated against a validation set derived from the augmented EMNIST dataset.
*   **Metric**: Average validation accuracy.
*   **Result**: The final model achieved an average validation accuracy of **~91%**.

#### 11.2. A/B testing

[NO INFO] (The feature is experimental and has not been released).

### 12. Integration and Serving

#### 12.1. Architecture

The system uses an on-device serving architecture. The model runs locally on the user's Android or iOS device.

#### 12.2. API and integration

1.  A custom UI component, `SketchBox`, is placed over each crossword square.
2.  The `SketchBox` listens for touch and drag events to capture the user's finger or stylus strokes as pixel data.
3.  A timing mechanism (500-1000ms delay) waits to ensure the user has finished writing the character.
4.  The captured image data is pre-processed (downscaled to 28x28, binarized) and fed into the TensorFlow Lite interpreter.
5.  The model performs inference and returns the predicted character.
6.  The application displays the recognized character in the crossword square.

#### 12.3. Infrastructure

*   **Model Format**: `.tflite`
*   **Model Size**: ~100KB
*   **Runtime**: TensorFlow Lite on Android and iOS.

#### 12.4. SLAs and fallback

*   **Latency**: No specific inference latency SLA is mentioned, but the design prioritizes a smooth user experience, with an input delay of 500-1000ms being a key parameter.
*   **Fallback**: The existing custom software keyboard serves as the implicit fallback input method.

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Retraining and maintenance

[NO INFO]

#### 14.2. Future work and enhancements

The article identifies several potential areas for future development:
*   **Error Handling**: Improving the model to handle partial letters and irregularly spaced letters.
*   **New Features**:
    *   "Scribble-to-Erase" detection.
    *   In-app self-training mechanisms to further improve the model with user data.
*   **Broader Vision**: Using on-device ML to open doors for other interactive features within the NYT Games app.