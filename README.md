💸✨ Expenzo – Where Every Rupee Counts ✨💸
Definition:
### Expenzo •எக்ஸ்பென்சோ •ಎಕ್ಸ್‌ಪೆಂಜೊ •एक्सपेन्ज़ो •エクスペンゾ •
##### adjective
    1.Discreetly aware of spending habits

    2.Quick to record and reflect on purchases

    3.Cautious and mindful with every rupee spent 💸
         


## 🇸​🇺​🇲​🇲​🇦​🇷​🇾​
Expenzo is a sleek, intuitive budgeting app built to help you take full control of your money. It tracks your spending and budgets in real time — making it easier to spend wisely, save better, and reach your financial goals faster.

With stunning visual breakdowns, Expenzo helps you see exactly where your money is going — whether it’s groceries, subscriptions, or those extra weekend takeouts 🍔🛍️.

🎯 Want to know how much you spent on food last month vs bills?
📊 Expenzo shows it in a tap — clear, colorful, and easy to understand.

Users can **login using Google** and their information is stored in a **firestore database** so that they can come back to their budgets at any time.

## Development Workflow
#### Dependencies
Dependencies used are listed in requirements.txt. You can create a virtual environment and then run 

> pip install -r requirements.txt

to install them all at once.

#### Configuration for Google login
1. In order to use Google's login authentication method, you need to create a client on Google Cloud Platform. [Follow these instructions](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid) to get a client ID and client secret. 
2. Download the generated client secret JSON file and add it to the project's parent folder (so as not to include it in the project files or accidentally upload online) as 'client_secret.json', or change the path referencing it in main.py.
3. Add the client id, client secret, and a [randomly generated secret_key](https://pyquestions.com/where-do-i-get-a-secret-key-for-flask) to a .env file using the provided .env.template file. 

#### Configuration for Google Cloud Firestore
You need to [create a service account](https://cloud.google.com/compute/docs/access/create-enable-service-accounts-for-instances) and get a JSON key on GCP console. Add this service account to the parent folder of the project (so as not to include it in the project files or accidentally upload online). Then set the credential environmental variable in your .env file:

> GOOGLE_APPLICATION_CREDENTIALS=[PATH TO SERVICE ACCOUNT JSON]

#### Running Flask server locally
You need to make sure that Flask knows where your app code is. You need to specify the file name of the flask app:

> export FLASK_APP=main

then you can run

> py -m flask run