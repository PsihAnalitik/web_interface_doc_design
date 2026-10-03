# Uncovering Hidden Insights in Customer Feedback

- **Sample ID**: case_097
- **Source URL**: https://medium.com/kingfisher-technology/uncovering-hidden-insights-in-customer-feedback-824daa16fa37
- **Content type**: article

---

TL;DR — Summary
We uncovered insights in Kingfisher’s customer surveys using an innovative topic modelling pipeline that combines LDA, BERTopic, and large language models (LLMs) generated topics using a deep neural network.
Why topic modeling?
Understanding the customer experience is crucial for businesses to grow and to be able to meet customer needs. At Kingfisher, we are committed to building a data-led customer experience by leveraging and accelerating the use of our data across all levels of our organisation, from the overarching group to our household name retail banners such as B&Q, Castorama, and Screwfix. One critical way we obtain customer insights is by collecting feedback across numerous channels, including product reviews on our websites and survey responses.
Qualitative data provides a wealth of information on the customer experience and their satisfaction at various touch-points. However, manually analysing unstructured text data like customer surveys to find key themes and insights is extremely difficult. As the amount of text data grows over time, so does the challenge of extracting meaningful information from it. Kingfisher needed an efficient way to structure and summarise insights from these rich sources of qualitative customer opinions and feedback.
Topic modeling provides a promising solution — an unsupervised machine learning technique to automatically detect topics and themes within a corpus of texts. In this blog, we demonstrate an innovative neural topic modeling pipeline, deployed with GCP’s Vertex AI Pipelines, to uncover and analyse key themes in customer survey responses from Kingfisher banners. For example, we can assess customer reaction to various initiatives, such as a newly launched loyalty program, a new approach to store layout and organisation, or a new feature in the B&Q app.
As Kingfisher introduces new programs, the pipeline provides a scalable way to gain insight into customer perceptions from qualitative survey data in the customers’ own words.
Benefits of Topic Modeling
Applying topic modeling to textual data provides several key benefits:
- Saving analyst time — Rather than having analysts read every survey response, algorithms can detect topics across all data automatically, thus empowering them to identify improvement opportunities more quickly.
- Discovering hidden topics — Topic models surface latent themes human analysts may not have realised existed in the first place. Letting the algorithm find patterns provides unexpected insights.
- Understanding meaning — The topic keywords and example responses give crucial context into the meaning of survey themes.
- Enabling exploration — Once responses are annotated with topics, they can be filtered, sorted, and visualised along different topic dimensions to explore topic interactions and relationships.
We leveraged these benefits by applying advanced neural topic modeling techniques to extract key themes and business insights from Kingfisher’s customer survey data in an automated, scalable way.
Introduction to Latent Dirichlet Allocation
Latent Dirichlet Allocation (LDA) is perhaps the most commonly used algorithm for topic modeling of text corpora. LDA is a statistical model that analyses patterns in large collections of text to automatically discover common themes or “topics” that run through them. It figures this out by detecting which words tend to appear together in documents.
The intuition behind LDA is that documents cover multiple topics in different proportions. The key assumptions are:
- Each document is a mixture of topics
- Each topic is a distribution over words
For example, a “power tools” topic may contain words like “drill”, “screwdriver”, “hammer”, “saw”, etc. A “customer service” topic may contain words like “service”, “helpful”, “friendly”, “knowledgeable”, etc.
The LDA algorithm tries to figure out the topics in the documents along with the topic distribution per document. The general workflow is:
- Randomly generate unique topics defined as word distributions
- Model each document as a random mixture over these topics
- Generate words by picking topics and then sampling from their word distributions
- Iteratively refine topics and document-topic distributions to improve coherence
After several optimisation iterations, LDA converges to accurate topics representing common themes, and meaningful document-topic distributions.
For our pipeline, we used LDA to analyse Kingfisher’s survey response text data to discover response themes. Our workflow is:
- Preprocess text into tokens, remove stopwords
- Create Document-Term Matrix of counts
- Train LDA model, determine optimal number of topics
- Output topics defined as word distributions + topic distributions per response
Analysing survey responses by their assigned topics gave a concise, data-backed summary of the key themes in the dataset!
Improving Interpretability with Contextual Embeddings
While LDA performs well for topic modeling, it lacks an understanding of word context and meaning due to relying on simple word counts. For example, the word “bank” in a financial context signifies something very different than “bank” in “river bank”.
BERTopic improves upon LDA by utilising contextual embeddings from large pre-trained language models like BERT. Rather than simply counting words, BERTopic first encodes the semantic meaning of words into vectors using BERT deep bidirectional representations, then clusters the vectors into topics. Despite its clustering approach, BERTopic is still able to represent documents as a mixture of topics to be represented for a document by creating a topic distribution.
We integrated BERTopic into our pipeline to leverage its more advanced contextual topic modeling capabilities. As our survey data covers complex themes requiring word sense disambiguation, BERTopic could create more cohesive topics less prone to word ambiguity issues.
Our BERTopic workflow:
- Pass text data into BERT model to create contextual document embeddings
- Group embeddings into topics via dimensionality reduction and clustering
- Compare topics to hand-labelled data to further refine model
- Assign topic probabilities to each survey response
BERTopic improved our topic coherence and meaning substantially vs LDA alone. Crucially, it could disambiguate words to accurately model context simply not possible with bag-of-words models like LDA. Our topics reflected the true themes using relevant multi-word phrases.
Combining Models via Hand-Labelled Projection
While LDA and BERTopic provided their own useful, yet distinct topics, we could improve further by strategically combining models. Human-labelled data is highly valuable for guiding topic models. However, our models still discovered novel topics unseen in the limited labelled set.
Our key innovation was training a feedforward neural network to project model topics into the human-labelled topic space. This allowed new discovery guided by human perspective:
- Train LDA on all survey data, outputting topic distributions
- Train BERTopic on all survey data outputting topic distributions
- Train neural network to predict human-labelled topics using model topics from both LDA and BERTopic as input features
- Project LDA + BERTopic topic distributions through a network to output refined, human-interpretable topic distributions
The neural network essentially learns patterns linking model topics and human-judged topics. This allows surfaced themes to be “translated” into refined topics more aligned with human understanding.
By strategically leveraging both models and human guidance, we extract richer, more meaningful topics than any individual method in isolation!
Using Large Language Models for Data Labelling
In addition to topic modeling, we leverage large language models (LLMs), via Kingfisher’s recently announced Athena Platform, to reduce the human effort needed for data labelling. LLMs can generate labelled examples from just a small number of seed labels in a process called “few-shot learning”.
By including a few examples in the prompt, the LLM can annotate many additional responses saving substantial human labelling effort. The neural projector can then learn from both true manually-labelled examples and noisier but abundant auto-labelled examples.
Active learning can further improve the LLM’s annotations by identifying any systematic labelling errors on underrepresented topics and requesting targeted human labels to address these cases.
By strategically incorporating LLMs into the pipeline, we drastically increased the amount of labelled data available while minimising additional human effort.
Conclusion
We applied topic modeling techniques such as LDA and BERTopic to survey response data to automatically extract insightful thematic trends from the unstructured text corpus. BERTopic in particular better handled word meaning and context by leveraging the power of semantically coherent BERT embeddings.
Our key innovation was training a neural network projector to map model topics into the human-judged topic space. This guided discovery from a human perspective, unifying the two models into a hybrid system which exceeded the performance of either individual model.
We further improved modeling efficiency by incorporating large language models (LLMs) via few-shot learning to reduce manual labelling effort by over 90%. Targeted active learning via stratified sampling allowed us to strategically select only the most informative samples for labelling.
Together, these methods enabled the accurate extraction of coherent, interpretable topics with minimal human effort. Our pipeline provides immense opportunity to automatically structure insights from unstructured text across use cases like customer feedback, product reviews and social posts.
The left chart in Figure 3 displays the topic distributions across all surveys collected for a specific banner. With topics assigned to each survey, the data can be analysed at an aggregated level to uncover insights, while also allowing users to drill down to individual survey responses as needed, as depicted in the right chart.
We can further utilise this insight to improve our response in processing customer feedback. By collecting survey data over time, we can perform time series analysis to detect anomalies in topic prevalence by location. If a topic all of a sudden appears much more frequently in a specific area, our automated monitoring and alerting system could trigger further investigation.
We’re excited to continue innovating in advanced topic modeling, few-shot learning, and active sampling. These tools help the banners deliver a data-led customer experience to both retain existing customers and grow the customer base — in turn growing sales and revenue!
If you are interested in joining us on our Data Science journey, please check out our careers page.
Co-author: