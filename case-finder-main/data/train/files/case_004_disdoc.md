- Company: Expedia
- Title: Traveling Just Got a Lot Smarter with Romie
- Technology area: Generative AI & LLM
- Source URL: https://medium.com/expedia-group-tech/traveling-just-got-a-whole-lot-smarter-with-romie-dfb9b21c07c5
- Content type: article

### 1. Problem definition

#### 1.1. Origin

The core problem is the friction and complexity involved in travel planning, particularly for groups. Coordinating a trip among friends or family often involves reconciling different preferences (e.g., one person wants a boutique hotel, another wants a resort), which complicates the decision-making process.

The system, named Romie™, is an AI assistant designed to address this by acting as a "travel agent, concierge and personal assistant all in one." It aims to assist travelers throughout their entire journey, from initial planning to in-trip support.

#### 1.2. Relevance & reasons

The existing flow for trip planning is manual and often fragmented. It involves extensive research, coordination via group chats, and difficulty in consolidating group preferences into a bookable trip. Romie is designed to streamline this by:

*   **Simplifying Group Planning:** Listening to group chat discussions to provide tailored suggestions.
*   **Personalizing Shopping:** Translating group chat discussions into a personalized shopping experience on Expedia.
*   **Consolidating Itineraries:** Pulling in bookings made on other platforms to create a unified itinerary.
*   **Providing Dynamic In-Trip Support:** Reacting to real-time events like flight delays or weather changes.

This is part of a broader company initiative to use AI and Generative AI to improve the traveler experience, which also includes features like:
*   **Destination Comparison:** Using GenAI to compare destinations based on themes (beach, family) and price.
*   **Air Price Comparison:** Combining price tracking with ML-driven insights to help users find the best time to book and travel.
*   **Guest Review Summary:** Using GenAI to summarize what guests liked and disliked about a property.
*   **GenAI-powered Help Center:** Providing summarized answers to user questions to reduce time spent reading articles.

#### 1.3. Expectations

The user-facing expectations for Romie are for it to be a multi-faceted assistant that helps with:

*   **Group Chat Trip Planning:** Can be invited to an SMS group chat to listen to plans and provide suggestions when prompted (e.g., "@Romie").
*   **Smart Search:** Can summarize the group chat and use that context to pre-populate the Expedia shopping experience, which users can then refine with filters (e.g., "rooftop views," "early check-in").
*   **Itinerary Building:** Can connect to a user's email to pull in external bookings and suggest nearby restaurants and activities.
*   **Dynamic Service:** Proactively monitors for disruptions (e.g., flight delays, bad weather) and provides alternative suggestions.
*   **Intelligent Assistance:** Maintains a real-time itinerary accessible to the group and can answer queries about trip status (e.g., landing time).

#### 1.4. Previous work

The document describes the existing manual process of trip planning as the status quo, implying this is a new automated approach to solve a long-standing user problem.

#### 1.5. Usage volumes and patterns

An "alpha version" of Romie is live in EG Labs for user testing. The intended usage pattern is multi-platform, involving:
*   SMS group chats.
*   Other messaging platforms like iMessage and WhatsApp.
*   The Expedia app.
*   Integration with user email accounts.

### 2. Goals and anti-goals

#### 2.1. Goals

The system is being built with three key principles in mind:

*   **Progressive Intelligence:** The system should get progressively more intelligent by learning from interactions and remembering user preferences (e.g., "love of boutique hotels, Italian food, and traveling with your dog").
*   **Meet Users Where They Are:** The assistant should be accessible across various platforms, including the Expedia app, iMessage, and WhatsApp.
*   **Assistive, Not Intrusive:** The assistant should be available on-demand ("at the ready") but not proactively interject without being prompted. It should wait to be called upon, like a "perfect waiter."

#### 2.2. Anti-goals

*   **Being Intrusive:** The system should explicitly avoid being intrusive and should only provide help when directly invoked (e.g., via "@Romie" in a chat).

### 3. Risks and constraints

*   **Technology Maturity:** The article notes that "AI, fundamentally, is a learning journey" and "not a silver bullet," acknowledging the risks associated with the effectiveness and reliability of the underlying AI technology.
*   **Development Stage:** The system is currently an "alpha version" available in "EG Labs." This constrains its current capabilities and availability, with the stated goal being to "learn fast, mature it quickly."
*   **Third-Party Dependencies:** The system relies on integration with external platforms for core functionality:
    *   SMS, iMessage, and WhatsApp for group chat features.
    *   User email providers for itinerary building.

### 4. Metrics and loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

The system leverages multiple data sources to function:

*   **User-Generated Content:**
    *   Text from SMS group chats where Romie is invited.
    *   User queries and filter selections within the Expedia shopping experience.
*   **User Account Data:**
    *   Booking information from user emails (requires user permission to connect).
    *   Learned user preferences stored over time (e.g., hotel type, food preferences, pet travel).
*   **Real-Time External Data:**
    *   Weather forecasts.
    *   Flight status information for disruption monitoring.
*   **Expedia Internal Data:**
    *   Hotel, flight, and activity inventory.
    *   Guest reviews for the "Guest Review Summary" feature.

#### 5.2. Labeling strategy

[NO INFO]

#### 5.3. Data quality issues and cleaning

[NO INFO]

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

The primary validation method described is releasing an "alpha version" in "EG Labs." This allows the team to gather real-world user feedback to "learn fast, mature it quickly, and build new experiences." No formal train/validation/test split methodology is mentioned.

### 7. Baseline solution

The implicit baseline is the existing manual, non-AI-assisted process for trip planning. This involves:
*   Users conducting their own research for destinations and activities.
*   Coordinating with friends and family in group chats without a central organizing tool.
*   Manually tracking bookings and itinerary details.
*   Reacting to travel disruptions without proactive assistance.

### 8. Errors and their analysis

The system is designed to handle a specific class of real-world "errors" or disruptions:
*   **Flight delays:** The system monitors for delays.
*   **Weather disruptions:** The system monitors for events like a "walking tour rained out."

In these cases, the system's function is to provide "alternative suggestions," turning a potential negative experience into a managed one. No other error analysis is described.

### 9. Training pipelines

[NO INFO]

### 10. Features

#### 10.1. Feature categories

Based on the system's functionality, the following categories of features are [inferred] to be used by the models:

*   **User Profile Features:**
    *   Learned preferences (e.g., affinity for boutique hotels, Italian food).
    *   Travel habits (e.g., travels with a dog).
*   **Group Context Features:**
    *   Preferences and constraints extracted from group chat conversations.
*   **Trip Context Features:**
    *   Destination, travel dates, budget constraints.
    *   Booked items (flights, hotels, activities).
*   **Real-Time Context Features:**
    *   Current weather at the destination.
    *   Real-time flight status.
*   **Item Features:**
    *   Attributes of hotels, flights, restaurants, and activities from Expedia's inventory.

#### 10.2. Feature selection

[NO INFO]

### 11. Measuring results

#### 11.1. Offline evaluation

[NO INFO]

#### 11.2. A/B test design

The current evaluation strategy is a public alpha/beta test via "EG Labs." The goal is to "learn fast" and "mature it quickly" based on user interaction and feedback. No formal A/B testing methodology is described.

#### 11.3. Reporting

[NO INFO]

### 12. Integration and Serving

#### 12.1. API design and integration

The system is designed for multi-platform integration:

*   **Messaging Integration:** Integrates with SMS, iMessage, and WhatsApp, allowing users to add Romie to group chats. It is invoked via an "@Romie" mention.
*   **Email Integration:** Connects to a user's email account to read booking confirmations from other travel sites.
*   **App Integration:** The context gathered from chats is brought "straight into your Expedia shopping experience" to personalize search and discovery.

#### 12.2. Serving architecture

The system operates as a real-time, interactive assistant, which implies an online serving architecture. It must be able to:
*   Respond to on-demand user requests in chat.
*   Continuously monitor external data sources (weather, flight status).
*   Update a shared itinerary in real time.

#### 12.3. SLAs and fallback strategies

*   **SLAs:** No specific latency or availability SLAs are mentioned.
*   **Fallback Strategy:** For travel disruptions like a flight delay or a rained-out activity, the system's defined behavior is to proactively find and present "alternative suggestions."

### 13. Monitoring

The system includes monitoring for real-world events that could impact a user's trip:
*   **Weather Monitoring:** "Keeps an eye on the weather."
*   **Disruption Monitoring:** "Looks out for last-minute disruptions."
*   **Itinerary State Monitoring:** "Constantly updating your itinerary in real time" so group members can check the latest plans.

No information is provided on monitoring for data quality, model quality, or engineering metrics.

### 14. Operations

The system is currently in an "alpha version" stage within "EG Labs," indicating that current operations are focused on rapid development, user feedback collection, and iteration rather than long-term maintenance. No details on retraining cadence, incident response, or ownership are provided.