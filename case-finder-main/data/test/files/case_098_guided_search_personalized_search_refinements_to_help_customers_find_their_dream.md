# Guided Search — Personalized Search Refinements to Help Customers Find their Dream Home

- **Sample ID**: case_098
- **Source URL**: https://www.zillow.com/tech/personalized-search-refinements/ 
- **Content type**: article

---

Zillow’s mission is to give people the power to unlock life’s next chapter. At Zillow AI — Core Search and Conversational AI, we do this by helping our customers find their dream home. Shoppers often need to look through many homes to find one that fits their unique needs. Now, we are making that process more intuitive through Guided Search, an experience which suggests personalized search refinements that help our customers narrow their searches.
Narrowing a search can be challenging with nearly 50 filters available to choose from. The large selection of filters isn’t itself the problem, as we want to provide many options for users to go deep and search on the criteria they care about. However, space on Zillow is premium real-estate (pun intended) and these filters have to be displayed within drop-down menus. As a result, it can sometimes be challenging for users to spot the filters they care most about.
We wanted to remove friction customers may experience in finding filters. To achieve that goal we added a new UI element — a limited set of buttons that we call search refinements. Through these buttons we can suggest the most relevant choice to the customers given the context. The challenge is then in ranking these refinements based on relevance.
Unsurprisingly, user search behavior changes significantly by location. To illustrate, in a warmer region having air conditioning or a backyard pool is likely to be popular; in a region with high population density on-site parking could be in demand. For refinement suggestions to be relevant, they need to take into account the regional information that drives shoppers to act in a certain way.
Another valuable source of predictive power for refinement suggestions comes from which criteria the shopper has already chosen. A larger home will have more bedrooms, bathrooms, and square footage than a smaller home, but an open land lot will have none of those attributes. By taking into account the choices already made by a customer, we can remove irrelevant refinements or select the best values for the relevant refinements.
In this article we will present a baseline model that suggests the most relevant search refinements, conditioned on the search region and the current set of applied filters.
We express the problem of selecting the most relevant refinements as a ranking problem. It is assumed that a user clicks on the refinement only if it is relevant to their needs. Also, the baseline doesn’t address placement bias. For ranking the refinements we model the probability that a user will click on them as follows:
P ( fi | F, g )
Here, fi represents the refinement candidate for suggestion, and F= {fa, fb …} represents the unordered set of refinements already applied at the time of prediction, such that fi, fa, fb … ∈ J where J is the set of all refinements; and g represents the search region. Thus we are modeling the probability that a customer will accept a refinement suggestion fi given that they are searching for properties in region g and have already selected refinements F. We can use these probability estimates in decreasing order to rank all possible refinement suggestions fi where fi ∈ J and fi ∉ F.
To estimate P ( fi | F, g ), we leveraged clickstream data of user actions on Zillow. From every search on Zillow, we extracted the filter state of the user at that time, as well as the region that the user was searching within. We then aggregated the count of unique users in each region g that had at least one query with all of the filters in F ∪ fi for all possible pairs of F and fi. To estimate the probability we normalized this count with the number of user in each region g that had at least one query with all of the filters in F. Using these probability estimates to rank all possible refinements forms a baseline model for refinement prediction.
Fundamentally, this model is based on the co-occurrence of filters, and this approach can be described as follows:
People who used filters A, B, C in your region ALSO used filter D.
This approach will perform well for the majority of use cases, but unfortunately, it misses one common pattern of filter usage on Zillow — while searching users often try multiple values for a filter to gain a better understanding of the market. For example, a user may set different price points to gauge what their money will get them. This pattern of filter usage isn’t supported by the model we described, as revisions to a filter do not co-occur within a search. To allow prediction of changing filter values, we apply a different approach which can be described as follows:
People who used filters A, B, C in your region THEN used filter D.
To model P ( fi | F, g ) we again use clickstream data; however, instead of using search events, we use filter change events. From each filter change event, we extract the previous filter state, the region, and the new value of the changed filter. We then aggregate, for all g, fi, and F, the number of unique users in each region g who had a filter change event with the new value fi where the filter state was F. This count, normalized, forms an estimate for the probability P ( fi | F, g ), which can predict filter revisions.
Of course, there are trade-offs. While this new model allows us to capture revisions to a filter, it requires more user data than our original formulation, as the order of fi and set F matters. On our dataset we see roughly a factor of 10 fewer events for equivalent predictions for this second approach when compared with the first. Given this tradeoff, we can use this model for regions where we have extensive user data, and the first model can act as a fallback when the second model doesn’t have sufficient training data to make a confident prediction.
Let’s take a look at what our baseline model is able to capture. The table below shows the top 5 filters (excluding beds, baths, price, and home type) predicted by our model for renters in the cities of Seattle, Phoenix, and Atlanta. There are similarities between the cities, of course — in-unit laundry matters a lot to renters everywhere. However, the model captures regional differences as well — filters for Pool and AC rank highly in the hotter cities, and the pet preferences of customers in each city score strongly as well. For example, in a spread out city like Phoenix, people may be more likely to own a large dog as opposed to a cat or small dog. The density of the city can also impact filter rankings — in a densely populated city like Seattle, on-site parking becomes an important requirement.
In addition to geographic information, the model also captures the context from filters in ranking possible refinements. The table below shows the relative rankings of different values for various numeric filters in Seattle, given that the user has already selected a filter for either 1, 2, or 3 beds. The rankings of various filters adjust to fit the needs of a user who has already told us they need a certain number of beds.
We are currently running an AB test, displaying these filter suggestions for users in a few select regions. As part of our test metrics, we are tracking engagement with the filters, home saves, and contacts to agents generated. Already, we are seeing early signs of positive impact. Most notably, we’ve seen a 33% lift in engagement with the filters displayed as refinements and positive impact on business metrics (e.g. saved homes, conversions).
With these indications of success, we are thinking about ways to improve upon our current results. Today, the filters that we surface as refinements are already available to users in the UI. However, Zillow has data on 200+ attributes for each property, and for some regions/users these attributes may be key. We can determine which home attributes are important for individual users as well as the overall region.
We can go beyond these structured attributes by extracting common keywords from home descriptions and using home clicks to rank those unstructured attributes as well.
Finally, now that this model is live, we can capture people’s interaction with the suggestions themselves and then use this as training data for statistical learning to rank models. These models and their successors in the future will allow us to improve the Zillow search experience, and help our customers find a home they will love to live in.
If you want to read more about how we use clickstream data at Zillow to optimize the shopping experience, you may be interested in this article on predicting sparse down-funnel events with transfer and multi-target learning.
Acknowledgements: Many thanks to Andrei Lopatenko, Arun Balagopalan, Farah Abdallah Akoum, and Xin Jin for their suggestions during the writing process. This is joint work with Adam Cohn, Andrei Lopatenko, Arun Balagopalan, Elysia Chu, Farah Abdallah Akoum, Kevin Zhao, Marie Laura-Luisada, and Zehua Zhou.
Related Articles
Subscribe to receive daily emails for the latest Zillow news and announcements, product updates and more.
---

## Extracted images (9)

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_098/img_001.png]
[IMAGE_ALT: Guided Search — Personalized Search Refinements to Help Customers Find their Dream Home]
[IMAGE_SOURCE_URL: https://www.zillowstatic.com/bedrock/app/uploads/sites/60/Hero-1-ae3a45.png]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_098/img_002.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/Figure_1-1-d9ea90.png]
[IMAGE_DESCRIPTION: 10 Saved Homes Seattle WA Rental Listings = : & ed erting $1,945/mo tho oe]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_098/img_003.gif]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/Figure_2-1-6b86b2.gif]
[IMAGE_DESCRIPTION: 00, eAo Allow large dogs Onsite parking Allow small dogs In-unit laundry Search Refinement Model]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_098/img_004.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/Guided_Search_Fig_4-1-6b86b2.png]
[IMAGE_DESCRIPTION: Allows Small Dogs Allows Cats Allows Large Dogs In-unit Laundry On-site Parking Allows Large Dogs In-unit Laundry Must Have Pool Must Have A/C Allows Small Dogs Allows Small Dogs Allows Large Dogs In-unit Laundry Must Have A/C Allows Cats]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_098/img_005.png]
[IMAGE_ALT: none]
[IMAGE_SOURCE_URL: https://wp-tid.zillowstatic.com/49/Guided_Search_Guided_Search_Fig_3-df80b5.png]
[IMAGE_DESCRIPTION: Previously selected filter Relative rankings of bath refinements Relative rankings of price refinements Relative rankings of parking refinements Relative rankings of square foot refinements 1 Bath 1.5 Baths $500K $600K S4OOK $300K 1+ Parking Spots 750 Saft 500 Saft 1000 Saft 2 Baths 1.5 Baths 1 Bath $500K $600K $700K $800K Garage 1+ Parking Spots 1000 Saft 1250 Saft 750 Saft 2 Baths 1.5 Baths 3 Baths $500K $600K $800K S1M Garage 2+ Parking Spots 2000 Saft 1500 Saft 1750 Saft]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_098/img_006.jpg]
[IMAGE_ALT: home for sale]
[IMAGE_SOURCE_URL: https://www.zillowstatic.com/bedrock/app/uploads/sites/60/2026/05/Header_For-Sale_1600x900_2-1280x720.jpg]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_098/img_007.jpg]
[IMAGE_ALT: women looking at computer]
[IMAGE_SOURCE_URL: https://www.zillowstatic.com/bedrock/app/uploads/sites/60/2026/05/Header_15-Years-of-FUB_1600x900-1280x720.jpg]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_098/img_008.jpg]
[IMAGE_ALT: michael sherman from Zillow Rentals at AIM conference]
[IMAGE_SOURCE_URL: https://www.zillowstatic.com/bedrock/app/uploads/sites/60/2026/05/Header-Image_AIM-Conference_1600x900_1-1280x720.jpg]
[IMAGE_DESCRIPTION: NO_TEXT_DETECTED]

[IMAGE_REF: ml-design-doc-reviewer/data/raw_documents/images/case_098/img_009.svg]
[IMAGE_ALT: illustration of mailbox]
[IMAGE_SOURCE_URL: https://delivery.digitallibrary.zillowgroup.com/public/mailbox-light_svg_Original.svg]
[IMAGE_DESCRIPTION: SKIPPED_SVG]
