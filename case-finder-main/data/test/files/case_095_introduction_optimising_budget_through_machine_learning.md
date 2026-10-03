# Introduction: Optimising Budget through Machine Learning

- **Sample ID**: case_095
- **Source URL**: https://medium.com/foodpanda-data/introduction-optimising-budget-through-data-analysis-030b2f39ad0c
- **Content type**: article

---

Introduction: Optimising Budget through Machine Learning
Objective
‘Bringing good food into your everyday’ — that is our mission at foodpanda. In order to achieve that, the company is constantly fulfilling the needs of our customers, riders & vendors.
The primary goal of the Marketplace Balance project is to achieve equilibrium between customer demand and rider supply through strategic budgeting measures. This involves creating a robust framework that enables us to allocate resources effectively, ensuring that there is a harmonious match between the influx of customer orders and the capacity of riders available to fulfil them.
To achieve this balance, the project will delve into data analysis, examining historical trends, peak demand periods, and rider availability patterns. Machine learning algorithms will be employed to forecast future demand and optimise rider deployment, enabling us to proactively address potential imbalances before they arise.
The ultimate objective is to create a marketplace environment where the fulfilment of customer orders is not only efficient but also economically sustainable. By implementing effective budgeting strategies based on a deep understanding of the demand-supply relationship, we aspire to enhance the overall user experience for both customers and riders while ensuring the long-term viability and success of our platform.
Context
When we invest heavily in Customer Acquisition & Retention Cost (CARC) to stimulate customer demand without adequately allocating resources for sufficient rider supply, it creates a marketplace of demand more than supply. Which means that our riders will not be able to fulfil all customer orders, resulting in missed revenues and poor customer experience. Conversely, having an excess supply of riders without a corresponding increase in orders leads to overspending on rider incentives. Furthermore, when riders sign up but struggle to earn, it contributes to their dissatisfaction and may drive them to choose competing platforms for work.
This project aims to predict the impact of allocating a specific amount of CARC incentives (X) to generate a certain number of orders (Y) and allocating a certain amount of rider payments (A) to achieve a particular rider fill rate (B). The goal is to enable the business to optimise budget allocation, considering it as a constraint, and prevent scenarios that could adversely affect financial performance and rider satisfaction.
Scope
The scope of this project only includes restaurants and delivery in foodpanda business. The recommendation will be in country & city granularity. The time granularity will be in 3 steps: daily, weekly and monthly. This is for the ease of use for users to budget on a monthly basis and check their budgeting accuracy on a weekly basis.
Our analysis on restaurant deliveries at the city level, aims to gauge the accuracy of the model, particularly in terms of its practicality for business applications. The ultimate objective is to develop a recommendation tool designed to assist users in making informed decisions regarding budget allocations for CARC Incentives and Rider’s Incentives.
Key metrics that matter to the business when budgeting are: Gross Merchandise Value (GMV), Fully Loaded Gross Profit per Order and Cost per Order.
Gross Merchandise Value (GMV) refers to the Gross final amount which the customer pays. It also includes Gross Food Value (GFV), Delivery Fee and Incentives.
Fully Loaded Gross Profit per Order (FLGPO) , refers to the profit the business makes after deducting costs like delivery fees, cost of sales and CARC incentives.
Cost per Order refers to the costs required to fulfil each order foodpanda has.
This tool offers predictions for key metrics such as Gross Merchandise Value (GMV), Profit, and Cost per Order associated with varying levels of CARC Incentives and Rider Incentives budgets. Users can leverage these predictions to gain insights into the potential outcomes of different budgetary scenarios.
In addition, the tool will illustrate the opportunity cost associated with the company’s growth objectives. Specifically, it will quantify the trade-offs involved in increasing CARC incentives to attract more orders, providing a clear understanding of the potential profits tied to such strategic decisions.
This comprehensive approach ensures that users are equipped with valuable insights to optimise their budget allocations in alignment with the company’s growth targets.
Potential Challenges
Several challenges are anticipated in the execution of this project, primarily stemming from short-term factors like weather conditions and time-limited promotions offered by vendors, for instance, McDonald’s seaweed fries. Adverse weather can lead to a surge in order demand but a decrease in the sign up & show up of riders for their shifts, as individuals are less inclined to work in inclement conditions.
Additionally, external factors, such as promotional campaigns initiated by competitors, pose another layer of complexity.
These external influences, however, will not be accounted for within the scope of our project as they are challenging to foresee and collect in our data.
As a result, our project will focus on excluding these factors from consideration. While acknowledging that days affected by factors beyond our control represent a small percentage of the overall year, the project’s core objective is to offer recommendations for days unaffected by weather, limited-time offers, and competitors’ campaigns.
By concentrating on days with fewer external disruptions, the project aims to provide more reliable and actionable insights for optimising budget allocation under more predictable conditions.
Assumptions
We are making a few basic assumptions in our project.
- Historical trends are accurate in predicting future trends
- Relationship of budgets have a strong correlation with GMV/Orders
The Requirements
Our project was initiated with the aim of developing an advanced recommendation tool tailored for Managing Directors to streamline budgeting processes for a city.
Upon engaging with diverse stakeholders and delving into the intricacies of the budgeting procedures and requirements, several key insights emerged:
- Top Line — Gross Merchandise Volume (GMV):
The overarching goal is to boost GMV, fostering the company’s growth and scalability. By strategically increasing GMV, the business positions itself for expansion and development.
2. Bottom Line — Gross Profit (FLGP):
Simultaneously, as efforts are directed towards elevating GMV to propel company growth, there’s a parallel need to ensure that profits are generated to cover overhead costs. The emphasis here is on achieving a balance that sustains both growth and financial stability.
3. Cost Per Order (CPO):
An essential factor in this equation is the Cost Per Order. As the endeavour is made to augment the number of orders, the strategy involves optimising CPO by allowing riders to efficiently handle multiple orders simultaneously. This stacking of orders not only enhances operational efficiency but also contributes to a reduction in overall costs per order.
In essence, our project is geared towards providing Managing Directors with a comprehensive recommendation tool that takes into account the interconnected dynamics of GMV, FLGP, and CPO. By aligning these elements, the tool aims to empower decision-makers in making informed and strategic budgetary decisions, fostering both growth and financial health for the city operations.
The Product
The product is presented through a Tableau Dashboard, leveraging the familiarity of our business users with the interface. The utilisation of Tableau affords us precise control over data access, ensuring a secure and tailored experience.
Upon accessing the dashboard, users are initially presented with an overview of the projected Gross Merchandise Volume (GMV) and order trends corresponding to varying budget amounts. This provides a comprehensive understanding of the anticipated outcomes associated with different budgetary allocations.
Furthermore, users have the capability to select a specific budget allocation, enabling them to visualise the recommended distribution of funds between CARC incentives and Rider payments. The dashboard is structured into three distinct sections, each corresponding to the specified requirements: Top line (GMV), Bottom Line (Profit), and Cost per Order (CPO).
An additional feature of the dashboard is a chart illustrating the tradeoff between Gross Profit (FLGP) and GMV. This graphical representation aids users in gauging the extent to which profits are sacrificed in pursuit of growth, facilitating informed decision-making.
To enhance data visibility, the dashboard incorporates a tabular chart presenting all relevant data in a clear and organised format. This comprehensive approach ensures that users can effortlessly navigate through different aspects of the budgeting recommendations, fostering a more intuitive and insightful user experience within the Tableau dashboard.
What have we achieved
We’ve developed a sophisticated recommendation tool designed for high-level budgeting purposes, specifically tailored for days unaffected by external factors such as weather, limited-time offers, and competitor campaigns. This tool meticulously incorporates the diverse considerations our users encounter during the budgeting process, addressing key elements such as top-line metrics, bottom-line profitability, and Cost per Order (CPO).
Overall, our accomplishment lies in the creation of a robust and user-friendly recommendation tool that not only considers various factors influencing the budgeting process but also empowers users to strategically navigate the dynamics between profitability and growth in their decision-making processes.
In most, if not all, businesses, the balancing act of generating demand and ensuring a healthy supply is crucial for sustained success. Striking the right equilibrium between generating demand for orders and maintaining a robust supply of riders is essential for meeting customer orders and maximising profitability. This delicate balance requires a strategic approach, leveraging data analytics, market research, and agile business practices to adapt to changing dynamics. Ultimately, achieving harmony between demand and supply not only fosters customer satisfaction but also enhances operational efficiency, positioning a business for long-term resilience and growth in a competitive landscape.
To gain further insights into the project’s methodology, it is detailed in the following: The Making: Optimising Budget through Machine Learning.
Also, Sculpturing: Optimising Budget through Machine Learning shares about the sculpturing of the project, in terms of establishing the project and forming the ways of working within the team.