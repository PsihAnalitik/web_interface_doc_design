# How we used Cross-Lingual Transfer Learning to categorize our content

- **Sample ID**: case_085
- **Source URL**: https://medium.com/dailymotion/how-we-used-cross-lingual-transfer-learning-to-categorize-our-content-c8e0f9c1c6c3
- **Content type**: article

---

How we used Cross-Lingual Transfer Learning to categorize our content
Dailymotion is a video platform hosting hundreds of millions of videos in more than 20 languages which are watched every day by millions of users. One of our main priorities is to provide the most suitable content to our users. This can be done only through a precise categorization of our videos no matter the language.
A year ago, Dailymotion presented how to predict the main categories of a video based on its textual metadata with sparse inputs in Tensorflow Keras. The results provided by using our Granular Topics generator for English and French videos encouraged us to investigate how to expand such results to other languages. How did we manage to transfer the results of our previous model to a larger set of languages?
A need for multilingual categories
One of the main issues a video hosting platform faces is to be able to automatically categorize a video, or improve the recommender system, for instance. At Dailymotion, we have already built a strong Deep Learning pipeline that automatically predicts the category of an uploaded video from its textual metadata (title, tags, description…) using a Bag-of-Words classification model.
Nevertheless, this solution has a major limitation: it only works for English and French videos. In fact, generalizing this method to other languages would be sub-optimal and would require a lot of hand-labeled data for every single language.
Moreover, other languages represent more than a third of our video catalog. As an international company, we needed to tackle this issue.
A Transfer Learning problem
There are several ways to tackle this issue with the appearance of strong multilingual NLP models such as m-BERT or XLM, but we chose to approach this as a Transfer Learning problem. In order to use the work previously done, we wanted to build a model that trains on English and French textual metadata but predicts on other languages.
“How is it possible to learn with English and French textual data and predict in other languages ?”
The objective of this article is to share how we were able to test and use new state-of-the-art multilingual NLP models in order to complete this cross-lingual classification task.
“To Translate or not to Translate, that is the question…”
One can wonder : Can you just simply translate all your textual metadata in English ? The answer is yes… and no. We can do this using the Google Translate API, for instance but this is a very trivial solution that would cost us a lot of money. In fact, we found a happy medium: a multilingual pre-trained model that can handle textual information in several languages.
What is a Multilingual pre-trained model?
The recent improvements in NLP research seem to converge to a specific type of model: heavy models trained on hundreds of millions of Wikipedia pages. These new models, as impressive as they are, can’t be retrained easily: during their trainings, they require a lot of computing power, often including dozens of Tesla V100 GPU.
Usually, these models have been trained once for a very general purpose. They are then available with pre-trained weights. Below is a short list of the multilingual pre-trained models that we have used during our research:
- m-BERT: a multilingual version of the now most famous NLP model, BERT. Trained on 104 languages, using shared Transformers.
- XLM: based on BERT architecture, XLM introduces a different training approach which is supposed to be more efficient for cross-lingual tasks.
- MUSE (Multilingual Universal Sentence Encoder): very different from the others, introduces a model focused on aligning embeddings.
Note: All these models are available in several versions (large, small, etc.). This article will present their application on a more concrete data science problem.
Complexity of our task
We want to train with English and French textual metadata and predict categories on other languages. This is called “Zero-Shot cross-lingual classification problem”. If all of the models presented above are all supposed to be multilingual, i.e, built in order to beat theoretical benchmarks on cross-lingual tasks such as XNLI, they are very often evaluated on simpler tasks.
Note: XNLI is an evaluation corpus for language transfer and cross-lingual sentence classification in 15 languages.
For a real-world data problem, you wouldn’t test these models in the same conditions as in a research paper. Below are examples of some issues that may occur:
- Complex data: since we are using the textual descriptions of our videos, the data is different from a Wikipedia page, for instance. In fact, these descriptions sometimes go straight to the point and contain abbreviations, or even spelling mistakes.
- Content distribution: in our case, we know that our video catalog can be different for each language or country. For instance, we know that our French video catalog contains more videos categorized as “Soccer” than Korea’s, due to the difference in culture between these two countries.
This is the reason why we needed to test and build our own implementation of these multilingual NLP models as we cannot blindly follow theoretical benchmarks.
What is a good cross-lingual model ?
Now that we have presented three multilingual models, we can explore how we decided between them.
The importance of aligned embeddings
All the state-of-the-art models presented in this article share a common structure: they take a sentence in input, convert its words into a sequence of tokens and then output an embedding. The main objective for these three multilingual models is to create a common vector space for all the languages. Nevertheless, the main difference between them is precisely this common vector space, i.e how they were trained and how their embeddings are built.
Although XLM and m-BERT do not share the exact same structure, they do share a common purpose: being able to perform on several cross-lingual tasks. For that reason, their training tasks are more general and the resulting embeddings are more complex, not simply aligned. On the other side, MUSE pre-training was focused on one goal: to create the most aligned embeddings possible, no matter the language.
“But… What do you mean by aligned embeddings ?”
MUSE was trained simultaneously on 16 languages with a shared encoder working with translation tasks. The result of that is a very good capability of mapping two similar sentences in two different languages in the same vector space. For instance, if MUSE encodes two sentences about Cristiano Ronaldo, one in English and the other in French, the resulting embeddings will be very similar. MUSE is not language specific. On the other hand, m-BERT and XLM embeddings are more general: they are not necessarily aligned per language but encode more information than that. Unfortunately, complexity can sometimes be a burden.
In theory, the MUSE shared representation between languages is better for a Zero-Shot Classification Task : if we use the embedding at the output of this model in input of our classifier, we will manage to get similar inputs for similar texts, no matter the language, without using any translation.
From embeddings to cross-lingual classifier
In order to really compare these pre-trained models, we present the following structure for our cross-lingual classifier:
- Input: Embedding. Obtained from the pre-trained multilingual models, by passing them the textual metadata of the video in input.
- Classifier core: Two Dense layers, followed by a Batch Norm layer and dropout.
- Output: Sigmoid, resulting into a vector with a confidence for each possible class. Thus, a video can have multiple class that characterize its content.
After testing all of the different multilingual pre-trained models, including both their small and large versions and days spent on hyper-parameters tuning, we found a winner.
The success of simplicity
Despite the huge amount of research articles about the surprising multilingual aspect of m-BERT or the incredible performances of XLM, our own conclusions are mixed.
BERT is dead, long live MUSE
We tried to test our architecture with different versions of both m-BERT and XLM, but neither of them gave us satisfying results. In fact, our task may be too different from the usual benchmarks. For a cross-lingual task like ours, bordering on a problem where large-scale translation would be required, it seems that MUSE in its lighter version, is far better than these very heavy pre-trained models based on the below Transformer architecture :
- Computing time: the lightest version of MUSE, based on CNNs, is able to compute an embedding three times faster than BERT or XLM, going from 8ms to 24ms on average for the models built with Transformers.
- Aligned Embeddings: as explained, we believe that for this task, the most important feature for a cross-lingual model is to provide aligned embeddings. MUSE is far better than the two others for that purpose.
- Global performances: we used a Top-1 accuracy in order to measure the performances of each model. We saw significant differences between these models in terms of metrics.
Overall, despite the actual popularity of Transformers-based NLP models, we believe that simplicity is key. This real-world project required a cross-lingual Transfer Learning model and MUSE, with its aligned embeddings per language seems to be the best solution.
What’s Next ?
- As already done for the English and French videos, this multilingual model is now in production. Each time a video gets uploaded on the platform, it is automatically tagged with a category.
- We will continue to improve the categorization of our video catalog by using other signals. For instance, we are currently working on a computer-vision based model that tags videos using their frames.