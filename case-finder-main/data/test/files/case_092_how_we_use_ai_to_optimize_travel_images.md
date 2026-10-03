# How We Use AI to Optimize Travel
Images

- **Sample ID**: case_092
- **Source URL**: https://www.getyourguide.careers/posts/how-we-use-ai-to-optimize-travel-images
- **Content type**: article

---

Key takeaways:
Yasamin Klingler, software engineer, will walk us through the challenges regarding the visual content and the solutions we use at GetYourGuide to improve the customer visual experience in our product and marketing channels.
{{divider}}
Images at GetYourGuide
At GetYourGuide, we manage millions of Images gathered from multiple sources such as our partners, tour providers, internal teams, and travelers. All these sources work towards the same goal, to bring the true essence of the activities to the travelers' eyes through accurate, aesthetically beautiful, and relevant images. At the same time, these images are used in different channels, each with their specific requirements.
Image lifecycle
Uploading process
The journey begins when one of the aforementioned sources tries to upload an image to our system. This image needs to be moderated and ensured that it is considered Safe For Work across various categories. Context is crucial; for instance, an image of a weapon might be suitable for a Museum of the Second World War tour while contextually incorrect for a Romantic Dinner Cruise tour.
Additionally, we rigorously scan the uploaded files for potential viruses and malware to ensure their safety before storing them on our side.
To optimize our storage and avoid a need for unnecessary deduplication, we aim to maintain a singular version of each image. For instance, If a supplier uploads a picture of the Eiffel Tower to the Eiffel Tower Summit Floor tour and the Eiffel Tower Summit Floor Ticket & Seine River Cruise, we do not want to store the same image per tour. For this reason, we would only keep one version of the image, referring to it with the hash of the image while keeping track of the references in which this image is being used.
Finally, once all the steps were successfully accomplished, the image lands on our object storage.
Recognition and processing
Now that we have the images uploaded, we employ a series of computer vision techniques to annotate, refine, filter, optimize, and prepare them to be served.
During the annotation stage, we initially leverage external APIs, such as Google Vision API to detect faces, landmarks, and many various tags available. Moreover, we train classification models internally for our company-specific concepts. For instance, our branding teams need to discern if an image aligns with our brand identity.
We generate multiple crop coordinates for every annotated image, focusing on the most significant elements. While we are able to serve the original version of the image in various sizes, the smart crops bring more value for smaller dimensions.
For instance:
While hashing images prevents us from displaying identical ones, it doesn't necessarily eliminate near-identical or highly similar images. Take, for instance, a tour of The Last Supper. While showcasing various images of The Last Supper can enrich the tour description pages, using three nearly identical images for our marketing campaigns would be redundant and less effective. Thus, addressing image diversity and detecting similarities remain crucial tasks.
For this reason, we detect similar images and filter the very similar ones for marketing campaigns.
Example: Image Similarity Detection
Every image can be numerically represented by its pixel values. One intuitive approach to detecting image similarities is to create a matrix for each image and then compare these matrices using basic distance metrics like Euclidean or Hamming distance. While this method might seem straightforward and effective for a small dataset comprising a few hundred images, it falls short when faced with even minor image alterations, such as varied cropping or rotations in a dataset of millions of images.
A more sophisticated approach involves identifying an image's key features or points. For instance, when comparing two RGB images of size 224 x 224, a direct pixel comparison would involve assessing approximately 150K points from each image without guaranteeing an exact match. In contrast, by utilizing image descriptors, we focus on comparing the most relevant image features, such as edges.
There are several techniques to generate these descriptors, including Speeded Up Robust Features (SURF) and Scale-Invariant Feature Transform (SIFT). Fig 3 illustrates the SIFT-generated descriptors. However, for our use case, we leverage the intermediate layers of EfficientNet to extract feature maps, as it demonstrated significantly better performance for image similarity learning on our image dataset.
To identify similar images within our collection, we must compare them against one another. This begins with preprocessing steps, such as resizing images to a consistent dimension suitable for our model, converting them to grayscale, and generating TensorFlow features. Subsequently, we utilize EfficientNet to produce embeddings of these preprocessed images.
Once we have these embeddings, we can pinpoint the nearest neighbors for a given image. To achieve this, we employ Facebook AI Similarity Search (FAISS), a rapid method designed for searching embeddings in multimedia documents.
By integrating these techniques, we can not only identify similar images but also curate a diverse selection of images.
Looking ahead
Throughout our journey at GetYourGuide, we consistently encounter unique challenges related to our visual content. This article endeavors to encapsulate a fraction of our initiatives, yet the potential in this domain is vast. As computer vision technology rapidly advances, leveraging cutting-edge technologies while maintaining their tangible business impact is crucial. Ultimately, our primary objective remains enhancing the visual experience of our travelers while enabling marketing channels to reach a broader audience and enable unforgettable travel experiences for as many travelers as possible.
Shoutout
I would like to thank Damien, Piotr, and Tündi for their collaboration in multiple stages of our image journey. To Joshua, Prateek, and Susanna for their contributions to this post.
---

## Extracted images (13)

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_001.avif]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/686d59ae73db94b6fc5f9db3_659e9c15174fb4fe59cb900a_yasamin-insidegetyourguide.avif]
[IMAGE_DESCRIPTION: OCR_RASTERIZE_FAILED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_002.avif]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/6873831b403ef4a65e3bb421_65ae4ee8327bda0561903ae9_inside-getyourguide.avif]
[IMAGE_DESCRIPTION: OCR_RASTERIZE_FAILED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_003.avif]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/6873831a403ef4a65e3bb3bc_659e99ade60637df3ad6275a_ai-travel-image-1-insidegetyourguide.avif]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_004.avif]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/6873831a403ef4a65e3bb3cc_659e9a6952312e86f5b74595_ai-travel-image-2-insidegetyourguide.avif]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_005.avif]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/6873831a403ef4a65e3bb3c0_659e9a8ada973e85aec20718_ai-travel-image-3-insidegetyourguide.avif]
[IMAGE_DESCRIPTION: 200 400 600 ° 250 S00 750 1000 1250 1500 1750]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_007.jpg]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/6a1ff0cc513b33eb33b6229a_Summit%20Week_Inside%20GetYourGuide.JPG]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_008.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/69a57ae5334d74a032bad713_GYG-logo-circle.png]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_009.jpg]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/6a0c5aea2558ed35ddd4569d_2026-05-05_Ayush%20Kumar-6.JPG]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_010.avif]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/686d59975fb7f47744003a83_66584c7647c24f5788e596e5_Ayush%2520Kumar.avif]
[IMAGE_DESCRIPTION: OCR_RASTERIZE_FAILED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_011.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/6a0332b88328b73f0bddbbf1_tech%20mentorship%20at%20GetYourGuide_thumbnail.png]
[IMAGE_DESCRIPTION: Tech mentorship at GetYourGuide]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_012.jpeg]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/686a7507fff14c231dc1e2bf/6a03329e93e00b537184c379_fabian%20and%20valentin.jpeg]
[IMAGE_DESCRIPTION: ~]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_013.avif]
[IMAGE_ALT: A smiling woman with dark hair and a bright orange sweater is seated, holding a pen, and looking towards someone off-camera to her right. A blurred "GET YOUR GUIDE" sign is in the background.]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/685e9f1453ce76c79366e268/6878ae5d0e2ddada652d17dd_69362b76fc30c08da6b73b23d5ea02d0b7bd6cde.avif]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_092/img_014.webp]
[IMAGE_ALT: A group of people working together with a big smile on woman's face.]
[IMAGE_SOURCE_URL: https://cdn.prod.website-files.com/685e9f1453ce76c79366e268/68a7ffbeb29882d87fee0e75_2023%20Science%20fair%20Ampere%20Summit%20week%20May%2012%20nr.17%201.webp]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]
