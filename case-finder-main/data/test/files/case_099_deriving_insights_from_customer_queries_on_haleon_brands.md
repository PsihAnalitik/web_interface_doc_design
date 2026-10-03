# Deriving insights from customer queries on Haleon brands

- **Sample ID**: case_099
- **Source URL**: https://medium.com/trusted-data-science-haleon/deriving-insights-from-customer-queries-on-haleon-brands-86f7e01b912c
- **Content type**: article

---

NLP at Haleon
Deriving insights from customer queries on Haleon brands
by Dr. Varshita Sher, Zohaib Khan
Introduction
Haleon has a world-class portfolio of category-leading global brands, including Sensodyne, Voltaren, Panadol, and Centrum, to name a few. Our brands are trusted by health professionals, customers, and people worldwide to improve the health and well-being of individuals and their communities. It is, therefore, a significant enabler if we can derive trends and patterns from the feedback, queries, and comments we receive from the people who use our products on a day-to-day basis.
In this blog, we will be discussing how we analysed consumer queries recorded by our Consumer Relations (CR) team across four products (Otrivin, Panadol, Theraflu, Voltaren) using NLP techniques, the technical challenges we faced, and the technical approach utilised.
P.S. Goes without saying, all of the analysis were performed keeping Responsible AI guidelines at the forefront.
Why do we need to analyse consumer feedback?
Analysing consumer feedback on social media channels is important for a variety of reasons, including:
1. Identifying customer needs and preferences: Social media is a powerful platform for customers to share their opinions and experiences with our brand or products. Analysing this feedback can help us gain valuable insights into customer needs and preferences, which can inform future product development and marketing strategies. For instance, there has been a significant shift in buying preferences with more people opting for products that are sustainably sourced.
2. Identifying potential opportunities: Analysing trends can help identify potential opportunities for new product development, particularly in areas where there is a significant unmet need. For instance, a new product line for kosher-certified ingredients in OTC medicines.
3. Meeting customer needs: Consumer health products are developed to meet specific customer needs, whether it’s treating a medical condition, improving overall health and wellness, or enhancing the patient experience. By analysing trends, companies can gain insights into evolving customer needs and preferences, which can inform product development strategies. For instance, in a post-covid world wellness is rising as a priority alongside health as consumers are gravitating away from the quick-fix fallacy.
4. Ensuring safety and effectiveness: The safety and effectiveness of consumer health products are paramount. By analysing trends, companies can identify potential safety issues, side effects, or drug interactions that may arise with certain products. This can inform further research and development, as well as improve patient safety. For instance, new claims can be studied based on concomitant drug use.
Importance of Consumer Feedback for Haleon
Haleon values innovation, data-driven decision-making, user-centricity, consistency, and an insights-driven approach. We capture the real user experience of consumers via consumer relations data, which provides insights to fuel our innovation pipeline and identify emerging consumer demands. A dashboard encapsulating all this information enables users to assess keyword trends in consumer inquiries data, driving the identification of potential new product ideas, claims, innovations, and Real-World Evidence.
Data and its background
In building out the dashboard, we utilised the timestamped data collected by the CR Team from Haleon social media channels over the past 2 years containing consumer queries in 5 different languages (the majority being in English, followed by Mandarin). All PII (personal identifying information) data were removed before EDA (exploratory data analysis). We also incorporated some search keywords that the stakeholders were interested in tracking across quarters. For instance, did gluten inquiries for Panadol increase across quarters in a given year? There was also some interest in tracking combination use across our products. For instance, are people using Panadol along with Paracetamol?
Our Approach
Broadly speaking, our pipeline consisted of seven main steps:
- Translating non-English queries to English using the GoogleTrans API.
- Removing stop words, punctuation, dates, etc. using
nltk
library - Converting all numeric values into words. For instance, 6 weeks becomes six weeks.
- Lemmatisation and stemming — both of which are useful techniques for identifying similar words after converting words to their root form.
Lemmatisation is the process of converting a word to its meaningful base form whereas stemming is the process of removing thelast few characters from a word. For example, lemmatise converts “caring” → “care” and stemming converts “caring” → “car”.
5. Getting the unique set of bi-grams and uni-grams words from the queries. For instance, creating unigrams for “ease back pain” generates three separate units — “ease”, “back”, and “pain” and a bigram generates two — “ease back” and “back pain”.
6. Calculating TF-IDF scores for unique words from Step 5. (Note: Higher the score, the more useful the word).
TF-IDF measures how relevant a word is to a document in a collection of documents.
7. Sorting the words from Step 6 in descending order of TF-IDF scores and keeping the top 250.
Having generated the most relevant words across the dataset, we begin categorising each customer query into the respective category. We do this by fuzzy matching the word to the textual description and assigning one of the pre-determined search keywords. The result is a csv
containing the search keywords and their respective counts which were visualised using a Power BI dashboard across quarters, products, and countries.
Below is a snapshot of one of the visuals from the dashboard that displays the trending keywords for Centrum — a Haleon brand.
Conclusion
A picture is worth a thousand words.
On the surface it might seem like getting insights from customers is straightforward, people have been doing it without computational analysis/AI models for years. In today’s fast-paced business landscape, understanding your customers and meeting their needs is even more crucial for success. That’s where a powerful dashboard comes into play, helping you track insights and patterns from consumer queries. At Haleon, the dashboard is actively helping teams spot emerging trends and patterns and enabling us to meaningfully meet our purpose of delivering better everyday health with humanity. giving us a competitive edge. By closely monitoring the frequency and content of consumer queries, we can identify shifts in demand, stay ahead of the curve, and adapt our offerings accordingly.
In conclusion, applying simple NLP techniques combined with a well-designed dashboard for tracking consumer queries can empower your business to make data-driven decisions, improve customer satisfaction, and ultimately thrive in a highly competitive market.