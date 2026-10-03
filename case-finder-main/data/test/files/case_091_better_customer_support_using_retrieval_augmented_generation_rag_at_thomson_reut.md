# Better Customer Support Using Retrieval-Augmented Generation (RAG) at Thomson Reuters

- **Sample ID**: case_091
- **Source URL**: https://medium.com/tr-labs-ml-engineering-blog/better-customer-support-using-retrieval-augmented-generation-rag-at-thomson-reuters-4d140a6044c3
- **Content type**: article

---

Better Customer Support Using Retrieval-Augmented Generation (RAG) at Thomson Reuters
High quality customer support is critical to business success. In this article, we’ll explain how we employed an AI-powered solution architecture known as RAG to deliver better, faster customer service. Read on to learn how we were able to reduce resolution times using a GPT 4 powered solution, coordinating the company’s research and customer success functions to deliver a solution.
Informing the way forward
First, a bit of background. Thomson Reuters is a leading business information and content technology provider, helping people all over the world make informed decisions that matter.
Our customers — attorneys, executives, government, media organizations, and beyond — navigate changing markets and increasingly complex regulatory environments affects society. Thomson Reuters’ flagship products like Westlaw, Practical Law, Checkpoint, and Reuters News deliver trusted content and technology professionals and institutions need to do their work well.
This is what the company means when it says it helps “uphold the rule of law, turn the wheels of commerce, catch bad actors, and report the facts”. Something Thomson Reuters summarizes as its purpose: to inform the way forward.
Of course, ensuring customers’ success with great technical support is a critical part of delivering on that purpose.
Customer support problems to solve?
The challenge of providing support to legal, tax domains
Thomson Reuters domain expertise and its customer support agents are no different. Agents need to be able to quickly make sense of an everchanging set of information across products to deliver to our customers, who are already experts in highly specialized fields.
Finding the signal in the noise, cognitive overload
The customer support agents need to be able to quickly navigate CRM, hundreds of thousands of knowledge base articles, manage tickets and get to a possible resolution for the customer. Situations when a recent resolution for a problem is found by one agent but is not available for others in a structured manner, which means they have to rely on person to person knowledge transfer. Which all leads to the customer agents being in a state of cognitive overload.
Keeping up with customers’ growing expectations
Lastly, and perhaps most important, is simply understanding how valuable providing support is to customers’ perception of your business. A recent survey for example reports that 78% of people say their customer support experiences determine whether to continue buying. A growing business requires great support.
Further, customers’ expectations are growing. 58% of those same customers state their customer service expectations are higher today than they were a year prior.
Not only is great customer support critical to sustain business, what is great customer support today is likely not good enough next year. Businesses need to continually invest to keep up. But how?
Surely, AI can help. Right?
Thomson Reuters has been empowering customers with AI to help make sense of large amounts of information for more than 30 years, delivering a large-scale natural language search system to market before Google even existed for example.
Now, recent advances in Large Language Models (LLMs) have kicked off a new era of what’s possible. It seems the wave of what were flimsy chatbots just a few years ago have suddenly re-emerged, much more capable. The ability of these LLMs to make large amounts of data accessible to people via natural language interfaces is impressive.
Surely, AI can be used to empower customer support reps, right? Yes, in fact, a recent survey on the state of AI in customer service reported 30% of respondents are already using AI to help resolve customer support requests faster, reducing average handling time.
This is where Thomson Reuters Labs worked with Retrieval Augmented Generation to build a solution which supercharged our customer support executives to get access to our domain knowledge in a better way.
Retrieval Augmented Generation
Retrieval Augmented Generation (RAG) is a recipe or pattern for ensuring factual generation of responses in large pre-trained language models (LLMs) — with the best intent of avoiding many of the pitfalls of LLMs such as factual inaccuracies (hallucinations) and inability to provide provenance (cite sources of information). It introduces a non-parametric component. [DJW(T1] [UT2] [DT3] The concept of RAG was founded in this paper back in 2021. But it has become a lot more prevalent with LLMs in the past few months.
Advantages of RAG:
1. Reduce hallucinations.
2. Provenance
3.More economical means to introduce new / update knowledge over retraining LLMs.
Why RAG
The latest generation of Language Learning Models (LLMs), have demonstrated remarkable ability to generate human-like text, making them potent tools for a variety of applications. However, the concern around issues like “hallucinations” and lack of provenance have prompted the industry as a whole to search for more efficient ways to use these models, without sacrificing quality or accuracy.
The introduction of non-parametric methods offers a potential solution to this challenge. While LLMs contain parametric knowledge learned during training, this knowledge is fixed once the model is trained, making it less adaptable to new, unseen information. In contrast, non-parametric methods allow for a flexible approach, enabling the maintenance and update of knowledge post-training. This adaptability can prove crucial in real-world applications where the data may evolve over time.
This confluence of computational power, the emergence of advanced LLMs, and the shift towards more flexible machine learning strategies is what makes this exploration timely and crucial. The blend of parametric and non-parametric approaches, as seen in Retrieval Augmented Generation (RAG), aims to strike a balance between leveraging the generalization abilities of LLMs and ensuring up-to-date, accurate responses. By harnessing the strengths of both methodologies, we have the potential to unlock a new level of efficiency and accuracy in AI technology, opening the door to even more transformative applications. This is why the question is not just relevant, but imperative to answer now.
Implementation
The end goal of this solution was to build a chatty interface for our customer support agents to get the most relevant solution from our curated database. There are two flows to the implementation as seen below, with one being the processing and indexing flow and the retrieval flow.
Processing and Indexing Flow:
In the processing and the indexing flow, we take the data from Knowledge base articles, CRM tools etc. and process these text files to chunks which can be converted into embeddings. These embeddings or dense representations are typically generated using deep learning techniques such as pre-trained language models like BERT (Bidirectional Encoder Representations from Transformers) or variants like RoBERTa, T5 or even through API such as OpenAI(text-embedding-ada-002).
These embeddings are stored in dense retrieval systems also known as Vector databases which has been explained in detail below.
Retrieval Flow:
The retrieval flow is where the core function of the RAG works, it consists mainly of two parts one the dense retrieval system and then the seq-to-seq model, and we will discuss about each in detail below:
Dense retrieval system:
A dense retrieval system aims to efficiently retrieve relevant documents or passages given a query. Unlike traditional sparse retrieval models that rely on sparse vector representations of documents or queries, dense retrieval models leverage dense vector representations of text.
In a dense retrieval system, documents or passages are encoded into dense vectors, forming an embedding space where the semantic similarity between text snippets can be measured. When a query is input, it is also encoded into a dense vector. The similarity between the query vector and the document vectors is computed using various distance metrics such as cosine similarity or Euclidean distance. The documents or passages with the highest similarity scores are considered the most relevant and returned as results.
Dense retrieval systems have gained popularity due to their ability to capture fine-grained semantic relationships between text snippets. They often achieve better performance than traditional sparse retrieval models in tasks such as document retrieval, passage ranking, and question-answering. Additionally, these models can be optimized for efficiency and can handle large-scale document collections with fast retrieval times.
There have been a lot of companies and open-source projects that have been getting into this space in the last few months in the form of vector databases which has seen a lot of growth because of the value it provides for LLM’s for domain specific data. Some examples of such DB’s are milvus, OpenSearch, pgvector, weaviate, pinecone etc. Recently pinecone raised $100 million on a valuation of $750 million, to get an idea on how hot the space is.
For our use case we used milvus which is an open-source vector database and used an opensource sentence transformer from huggingface `all-MiniLM-L6-v2`.
Seq-to-Seq model:
The most relevant data fetched from the dense retrieval system is fed into a seq-to-seq model which is usually an LLM. This LLM in most cases nowadays is OpenAI’s GPT-4, as it has demonstrated state of the art performance. However, numerous open source LLMs perform well too such as LLAMA, MPT, Falcon etc.
We used OpenAI’s GPT-4 API. So, the most relevant context is concatenated along with the prompts and is sent to the API to get appropriate response for the user.
Impact
Below you can see the impact of RAG on fetching information on our domain data with and without RAG.
To GPT-4 Without RAG:
Question:
1040 e-file error: IND-041Error\nIf ‘ThirdPartyDesigneeInd’ in the return has a choice of ‘Yes’ indicated, then ‘ThirdPartyDesigneePIN’ must have a value.
Response:
The error message you're seeing, "1040 e-file error: IND-041 Error: If 'ThirdPartyDesigneeInd' in the return has a choice of 'Yes' indicated, then 'ThirdPartyDesigneePIN' must have a value", indicates that there is a problem with the Third Party Designee section of the tax return that's being e-filed.
In the United States, taxpayers can authorize another person (a Third Party Designee) to discuss their tax return with the Internal Revenue Service (IRS). If you have indicated "Yes" to the question asking if you want to allow another person to discuss this return with the IRS, then you are required to provide that person's Personal Identification Number (PIN) in the 'ThirdPartyDesigneePIN' field.
Here's what you can do to fix this:
1. Go back to the Third Party Designee section of your tax return.
2. If you've indicated "Yes" to allow a Third Party Designee to discuss your return with the IRS, ensure you provide the correct PIN for the third party in the 'ThirdPartyDesigneePIN' field.
3. If you do not want to designate a third party, change the 'ThirdPartyDesigneeInd' field from "Yes" to "No". In this case, you will not need to provide a 'ThirdPartyDesigneePIN'.
4. After making these corrections, try e-filing your tax return again.
Remember, each software may have different steps to follow to reach this part of the return, so if you're having trouble, you might want to check with the software's support system or instructions.
Though the above response does look like it makes sense this is not the most accurate response to solve the issue.
To GPT-4 With RAG:
Question:
1040 e-file error: IND-041Error\nIf 'ThirdPartyDesigneeInd' in the return has a choice of 'Yes' indicated, then 'ThirdPartyDesigneePIN' must have a value.
Response:
These are the steps that need to be followed for solving your issue:
1. Go to the Organizer.
2. Click on General Information.
3. Open Basic Return Information.
4. Click on Paid Preparer Information.
5. Correct any fields in the Third Party Designee section.
This response is most accurate as this match with the resolution to solve the issue within our products with the most recent information.
Conclusion
High quality customer support is critical to business success. In this article, we explained how we employed an AI-powered solution architecture known as RAG to deliver better, faster customer service. We were able to reduce resolution using a GPT 4 powered solution, coordinating the company’s research and customer success functions to deliver a solution.