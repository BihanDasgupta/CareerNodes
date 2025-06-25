ılıılı This repository contains the source code for 〽 CareerNodes: A Graphical Internship Matchmaker ❤︎ Powered by AI. ılıılıı


🔗 Publicly Deployed Website: https://careernodes.streamlit.app/


ılıılı Purpose: 

〽 This website is an internship match-maker designed for students of all education levels, from high school to grad school, to find internships that are more tailored to them faster and easier. 
Powered by GPT-4o, CareerNodes does a thorough analysis of the user's inputted information to find the best matches, outputs a compatability score, and provides an explanation of why each internship is good for the user. The website also provides a graphical representation of the user's spacial relationship with the internships listed based on the GPT-produced scores. 
In summary these features allow for the user to find good listings curated to them, recieve an explanation on why it is a good fit, and more uniquely get a visual representation of the internships in relation to them.


ılıılı Details/Walk-Through:

〽 Users are prompted to put in their information, including the following: GPA, education level, current school, current or intended major, skills, work type, preferred location, preferred industry, organixation type, schedule, and salary. They are then able to attatch their resume and optionally specify their preferred internship timeline through a calendar feature.
They can then click on the "Find Matches", which will result in a 1-2 minute wait time for the AI to produce results. Once results are generated, the top 20 internship matches will be posted below. Each listing will contain the job title and match score, along with basic and quick web-scraped information on its location, salary, schedule, and industry. A link to the job posting will be provided, as well as the expandable job description and an expandable explanation from the AI on why this job is a good fit for the user. 
Below all of the listings at the bottom of the website will be a graph visually representing the distances from a centered node representing the user and each job listing based on its respective similarity score. The user must zoom in to view the node labels containing the job title, score, and a url. The graph is both zoom-able and adjustable, and the user can move around the nodes if they please. The nodes are also color-coded based on spacial distance.


ılıılı APIs Used:

〽 Adzuna ~ To scrape all available internship listings in Adzuna's website 
〽 GPT 4o ~ Recieve corpus from Adzuna as well as user input 


ılıılı Technologies Used:

〽 Streamlit – For the frontend framework and deployment

〽 OpenAI GPT-4o API – For scoring, enrichment, explanation

〽 Adzuna API ~ As the internship data source

〽 PyPDF2 – For resume parsing

〽 NumPy – For similarity calculations

〽 PyVis / NetworkX – To create the network graph visualization


ılıılı Limitations and Future Implementations:

〽 This website only takes in listings from Adzuna, which only provides a small dataset of internship listings compared to all of the listings on the web. GPT does not currently provide an API that can perform web searches itself, so the only accessible option for me at this time was to feed it a limited dataset.
However, there are APIs such as Perplexity that can perform web searches and would be highlighy beneficial for the purpose of this website. My future implementation plan when/if possible is to get rid of the Adzuna API entirely and replace it with Perplexity, doing a web search for listings and feeding them to GPT 4o for an analysis in cross-reference to the user. Of course this will be very costly and I need to get approval from Perplexity for the API first.
When I get the chance, I would also like to add a chatbot feature for the user to ask the AI for application and job search assistance, or just any career-related advice in general. This can just be done with my current GPT 4o API but if I add in Perplexity it will again be far less limited and far more accurate and stable.


ılıılı What Makes CareerNodes Unique?

〽 CareerNodes is similar to existing features such as Linkedin or ZipRicruiter job postings. However, those existing features are part of a larger website which requires you to log in and subscribe to their emails, taking your data along with them. In that sense CareerNodes provides a much faster, more secure, and simpler/less irritating to navigate service.
CareerNodes also provides key additional features that are not currently available through existing job search applications: 
    ➤ 1) It performs an in-depth analysis of the user's detailed credentials, cross-checks it with each job recomendation, and provides an EXPLANATION curated to the user on WHY this internship is recommended to them. 
    ➤ 2) It gives the user a SIMILARITY SCORE to quantify how good of a match each recommended postings are.
    ➤ 3) It has a VISUAL COMPONENT that allows the user to VISUALIZE the SPACIAL DISTANCE between them and the recommended job postings based on the analyzed similarity score as represented by a GRAPH with nodes and edges.
 Over all, it is made for the purpose of helping the students find an internship through a more navigatable aesthetically pleasing UI and visual aid, and is tailored to the student's needs. Conversely, most existing job posting services are created with the intention of advertising the job itself rather than aiding the applicant in finding the best possible option. 


ılıılı To Run Locally:

➤ 1) Clone the repo:
    git clone https://github.com/your-repo-name/careernodes.git
    cd careernodes

➤ 2) Install dependencies:
    pip install -r requirements.txt

➤ 3) Create a .env file with the following API keys:
    ADZUNA_APP_ID=your_adzuna_app_id
    ADZUNA_APP_KEY=your_adzuna_app_key
    OPENAI_API_KEY=your_openai_api_key

➤ 4) Run the app:
    streamlit run CareerNodes.py


ılıılıılıılıılıılı Hope You Enjoy and Good Luck on Your Internship Journey! ılıılıılıılıılıılı
