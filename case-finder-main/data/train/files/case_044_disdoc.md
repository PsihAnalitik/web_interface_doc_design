- Company: Swiggy
- Title: Neural Search
- Technology area: Generative AI, Search
- Source URL: https://bytes.swiggy.com/swiggys-generative-ai-journey-a-peek-into-the-future-2193c7166d9a
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The core problem is that choosing what to order from the multitude of options available on the Swiggy app can be a daunting task for users. The existing search functionality requires users to use or remember specific keywords, which limits discovery and can be unintuitive. The goal is to create a more natural and conversational way for users to find food and groceries.

The system, referred to as "neural search," is designed to understand open-ended, conversational user queries and provide tailored recommendations.

Example queries include:
*   "I just finished my workout. Show me healthy lunch options."
*   "Show me vegan-friendly starters."

#### 1.2. Relevance & reasons

The primary reason for developing this system is to alleviate the user pain point of decision fatigue and make the discovery process "fun and effortless." By enabling conversational search, Swiggy aims to:
*   Improve the discoverability of specific items from its large catalog.
*   Open up the top of the funnel for broader, less-specific user queries.
*   Make the platform more intuitive and efficient for finding food, groceries (on Swiggy Instamart), and restaurants (on Swiggy Dineout).

#### 1.3. Expectations

*   **Functionality**: The system must understand conversational and open-ended queries and provide personalized recommendations in response.
*   **Performance**: The system is expected to respond to queries in real-time.
*   **User Interface**: The initial implementation is text-based search, with future plans to support voice-based queries.
*   **Scope**: The neural search capability will be used for food discovery, Swiggy Instamart (groceries), and a conversational bot for Swiggy Dineout.
*   **Localization**: The system will eventually support queries in select Indian languages.

#### 1.4. Previous work

The article implies the existence of a previous search system that was likely keyword-based and less effective for open-ended discovery. The new neural search is designed to overcome the limitations of this prior system.

#### 1.5. Usage volumes and patterns

*   **Catalog Size**: The system needs to search over a food catalog of 50 million-plus items.
*   **Traffic**: The feature is planned for a pilot, with the goal to eventually roll it out to "all search traffic" on the Swiggy app.

### 2. Goals and anti-goals

#### 2.1. Goals

*   Enable users to search using conversational, open-ended queries instead of specific keywords.
*   Provide personalized and tailored recommendations based on the user's intent.
*   Improve the discoverability of items across the catalog, especially for broad queries.
*   Deliver responses in real-time.
*   Develop the capability in-house to ensure greater control, faster iteration, and flexibility.
*   Expand functionality to support voice queries and multiple Indian languages.

#### 2.2. Anti-goals

[NO INFO]

### 3. Risks and constraints

*   **Technical Constraints**: The system must be able to provide responses in real-time while searching a catalog of over 50 million items.
*   **In-house Development**: The decision to build the solution in-house gives Swiggy more control and faster iteration times but also implies bearing the full cost and complexity of developing and maintaining a sophisticated LLM-based system. [inferred]

### 4. Metrics and loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **User Queries**: The model is adapted using "Swiggy-specific search data," which includes user search queries. [inferred]
*   **Food Catalog**: A catalog of over 50 million items, including dishes, recipes, and restaurant information.
*   **Item Metadata**: The catalog is being enriched with images and detailed descriptions of items, generated using other generative AI techniques. This is intended to help users understand unfamiliar dish names like "Chicken Dominator" pizza or "Nool Appam."

#### 5.2. Labeling strategy

[NO INFO]

#### 5.3. Data quality issues

A known issue is that "unfamiliar dish names can sometimes be perplexing" for users. The project addresses this by using generative AI to enrich the catalog with comprehensive dish descriptions and increased visual coverage.

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

[NO INFO]

### 7. Baseline solution

The implicit baseline is the existing search system on the Swiggy app, which requires users to "use or remember specific keywords." The new neural search system is designed to outperform this baseline by handling conversational and open-ended queries.

### 8. Errors and their analysis

The article mentions that the model has been fine-tuned to "respond accurately to relevant food-related queries," but provides no details on error analysis or specific failure modes.

### 9. Training pipelines

#### 9.1. Model and Architecture

*   The core of the system is a Large Language Model (LLM).
*   The model has been adapted and fine-tuned specifically for Swiggy's use case.

#### 9.2. Training Process

*   The model underwent a "meticulous two-stage process" for fine-tuning.
*   The fine-tuning process adapted the LLM to understand terminology related to dishes, recipes, restaurants, and Swiggy-specific search data.
*   The goal of the tuning was to ensure the model responds accurately to relevant food-related queries.

#### 9.3. Tooling

*   The capabilities were developed "in-house," giving Swiggy greater control over the product and faster iteration time. No specific frameworks or platforms are mentioned.

### 10. Features

*   **Input Features**: The primary input is the user's search query, which can be a conversational, open-ended phrase. This will eventually include text and voice inputs.
*   **Data Features**: The system leverages a food catalog of 50 million+ items, which is enriched with:
    *   Dish names
    *   Recipes
    *   Restaurant information
    *   Images
    *   Detailed item descriptions

### 11. Measuring results

#### 11.1. Offline evaluation

[NO INFO]

#### 11.2. A/B test design

*   **Rollout Strategy**: The feature will be launched in a pilot by September.
*   **Decision Criteria**: Based on the "learning and results" from the pilot, a decision will be made to roll it out to all search traffic. The specific metrics for this decision are not stated.

### 12. Integration and Serving

#### 12.1. API design

*   The system serves recommendations in response to user queries entered into the search bar of the Swiggy app.
*   It is designed to be conversational.
*   Future integrations include support for voice-based queries.

#### 12.2. Serving architecture

*   The system is required to provide responses in "real-time."
*   The capabilities are developed in-house.

#### 12.3. Applications

The neural search functionality is being integrated into:
*   The main Swiggy app for food discovery.
*   Swiggy Instamart for discovering groceries and household items.
*   A "Dineout conversational bot" to guide users in exploring dining options based on preferences like ambiance, cost, and ratings.

#### 12.4. Fallback strategy

[NO INFO]

### 13. Monitoring

[NO INFO]

### 14. Operations

#### 14.1. Retraining and updates

The choice of an in-house solution was partly motivated by the need for "faster iteration time" and the "flexibility to adapt to changing market trends," suggesting that a process for continuous improvement and model updates is in place.

#### 14.2. Rollout and release

*   A pilot is scheduled for September.
*   A full rollout to all search traffic is contingent on the results of the pilot.

#### 14.3. Other GenAI Initiatives

Beyond neural search, Swiggy is also using generative AI for:
*   **Customer Service**: Collaborating with a third-party to develop a GPT-4 powered chatbot for efficient and empathetic service for frequently asked questions.
*   **Partner Support**: Piloting in-house tuned LLMs to create a conversational assistant for restaurant partners. This assistant, available in the owner app and via WhatsApp, helps with onboarding, ratings, payouts, and other queries to enable faster issue resolution.