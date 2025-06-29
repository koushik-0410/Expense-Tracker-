import imp
import os
from datetime import timedelta
from dotenv import load_dotenv
import pathlib
import requests
from flask import Flask, session, abort, redirect, request, render_template
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import bcrypt
import hmac
import hashlib
from base64 import b64encode
from pip._vendor import cachecontrol
import google.auth.transport.requests
from functools import wraps

import database

app = Flask(__name__, template_folder="templates")
app.config['APPLICATION_ROOT'] = '/'
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_DOMAIN'] = '.charypie.com'
app.config['TEMPLATES_AUTO_RELOAD'] = True

app.config["SESSION_PERMANENT"] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

# Load environment variables and set secret key
load_dotenv()

app.secret_key = os.getenv("SECRET_KEY")
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Get the path to the client secret JSON file generated 
# using Google Cloud Platform
secret_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=secret_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="https://www.charypie.com/google/auth"  
)

###################################
# Non-protected pages that can be #
# viewed by any user              #
###################################

@app.route("/")
def renderHome():
    return render_template('index.html', loggedIn=isLoggedIn(), nav=renderedNav())

@app.route("/about")
def render🇦​🇧​🇴​🇺​🇹​():
    return render_template('about.html', loggedIn=isLoggedIn(), nav=renderedNav())

@app.route("/login")
def renderLogin():
    return render_template('login.html', loggedIn=isLoggedIn(), nav=renderedNav())

@app.route("/signup")
def renderSignup():
    return render_template('signup.html', loggedIn=isLoggedIn(), nav=renderedNav())

@app.route("https://koushik-2006.github.io/Expense-Tracker-/templates/privacy-policy.html")
def renderPrivacyPolicy():
    return render_template('privacy-policy.html', loggedIn=isLoggedIn(), nav=renderedNav())

@app.route("https://koushik-2006.github.io/Expense-Tracker-/templates/tos.html")
def renderTermsService():
    return render_template('tos.html', loggedIn=isLoggedIn(), nav=renderedNav())

@app.route("https://koushik-2006.github.io/Expense-Tracker-/templates/contact.html")
def renderContact():
    return render_template('contact.html', loggedIn=isLoggedIn(), nav=renderedNav())

####################################
# Functions for logging in and out #
####################################

def login_is_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if (session.get("google_id") is None) and (session.get("chary_id") is None):
            return abort(401)
        else:
            return function()

    return wrapper

def isLoggedIn():
    if (session.get("google_id") is None) and (session.get("chary_id") is None):
        return False
    else:
        return True
    
def renderedNav():
    if isLoggedIn():
        return """
            <ul>
                <li><a href='/'>Home</a></li>
                <li><a href='/about'>🇦​🇧​🇴​🇺​🇹​</a></li>
                <li><a href='/dashboard'>Dashboard</a></li>
                <div>
                    <img id='nav-profile-icon' class='profile-icon' src='https://koushik-2006.github.io/Expense-Tracker-/static/images/profileImages/undraw_blank.svg' alt='Profile image button that opens profile options'/>
                    <div id='profile-options' style='display: none;'>
                        <a href='/profile'>Profile</a>
                        <a href='/logout'>Log Out</a>
                    </div>
                </div>
            </ul>
        """
    else:
        return """
            <ul>
                <li><a href='/'>Home</a></li>
                <li><a href='/about'>🇦​🇧​🇴​🇺​🇹​</a></li>
                <li><a href='/login'>Sign In</a></li>
                <li><a href="/signup">Sign Up</a></li>
            </ul>
        """

@app.route("/google")
def googleLogin():
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session["state"] = state
    session.modified = True

    return redirect(authorization_url)

@login_is_required
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/google/auth")
def google_auth(): 
    flow.fetch_token(authorization_response=request.url)

    if not session.get("state") == request.args.get("state"):
        abort(500)

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=CLIENT_ID,
        clock_skew_in_seconds=5
    )

    if (id_info.get("email_verified") == True):
        session.permanent = False
        session["google_id"] = id_info.get("sub")
        session["name"] = id_info.get("name")
        session["email"] = id_info.get("email")
        session["credentials"] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token
        }
        user = database.getUser(session["email"])
        if not user:
            createUserGoogle()
        return redirect("/enter")
    else:
        abort(403)

@app.route("/chary/auth/validate", methods=['POST'])
def chary_auth(): 
    try:
        givenEmail = request.json["email"]
        givenPassword = request.json["password"]

        potentialUser = database.getUser(givenEmail).get('data')

        if (potentialUser == None):
            return {
                "status": 400,
                "message": "We could not find an account with that email. Try signing up for a new account."
            }
        if (potentialUser.get('google') == False):
            salt = potentialUser.get('salt').encode("utf-8")
            hashedPassword = potentialUser.get('password').encode("utf-8")
            # Hash the provided password and compare it to the hash in the database
            givenPassPepper = hmac.new(b64encode(os.getenv("SECRET_PEPPER").encode("utf-8")), b64encode(givenPassword.encode("utf-8")), hashlib.sha256).digest()
            givenPassHash = bcrypt.hashpw(b64encode(givenPassPepper), salt)

            if (givenPassHash == hashedPassword):
                session.permanent = False
                session["email"] = givenEmail
                session["chary_id"] = b64encode(os.urandom(32))
                return {
                    "status": 200,
                    "message": "Login successful!"
                }
            else:
                return {
                    "status": 400,
                    "message": "The password provided is not correct."
                }
        else:
            return {
                "status": 400,
                "message": 'This email was used to sign up via Google Sign In. In order to log in, please click the "Sign in with Google" button.'
            }
    except Exception as e:
        return {
                "status": 400,
                "message": str(e) + "."
            }


@app.route("/data/create-user/chary", methods=['POST'])
def createUserChary():
    email = request.json["email"]
    username = ""
    password = request.json["password"]
    image = ""
    color = ""
    currency = ""
    tutorialFinished = False
    profileCreation = False
    google = False

    salt = bcrypt.gensalt()
    pepperedPass = hmac.new(b64encode(os.getenv("SECRET_PEPPER").encode("utf-8")), b64encode(password.encode("utf-8")), hashlib.sha256).digest()
    hashedPass = bcrypt.hashpw(b64encode(pepperedPass), salt)

    try:
        database.createUser(
            email, 
            username,
            hashedPass.decode("utf-8"),
            salt.decode("utf-8"),
            image,
            color,
            currency, 
            tutorialFinished, 
            profileCreation,
            google 
        )
        
        session["email"] = email
        session["chary_id"] = b64encode(os.urandom(32))

        return {
            "status": 201,
            "message": "Creation successful!"
        }
    except Exception as e:
        return {
            "status": 400,
            "message": str(e)
        }

@app.route("/data/create-user/google", methods=['POST'])
def createUserGoogle():
    email = session["email"]
    username = ""
    password = ""
    salt = ""
    image = ""
    color = ""
    currency = ""
    tutorialFinished = False
    profileCreation = False
    google = True

    try:
        database.createUser(
            email, 
            username,
            password,
            salt,
            image,
            color,
            currency, 
            tutorialFinished, 
            profileCreation,
            google 
        )
        return {
            "status": 201,
            "message": "Creation successful!"
        }
    except Exception as e:
        return {
            "status": 400,
            "message": str(e)
        }

#######################################
# Pages that need authenticated login #
#######################################
@app.route("/enter")
@login_is_required
def redirectUserEnter():
    user = database.getUser(session["email"])
    if user["data"] and user["data"]["profileCreation"] == True:
        return redirect("/dashboard")
    else:
        return redirect("/form/create-user")

@app.route("/dashboard")
@login_is_required
def renderDashboard():
    refresh = request.args.get("refresh")
    tab = request.args.get("tab")
    if refresh == None:
        if tab == None:
            return render_template('dashboard.html', refresh="true", tab="overview", nav=renderedNav())
        else:
            return render_template('dashboard.html', refresh="true", tab=tab, nav=renderedNav())
    else:
        return render_template('dashboard.html', refresh=refresh, tab=tab, nav=renderedNav())

@app.route("/expand-budget")
@login_is_required
def renderBudget():
    currentDate = request.args.get('date')
    period = request.args.get('period')

    startDate, endDate = database.getCurrentStartEnd(currentDate, int(period))
    
    return render_template('budget.html', id=request.args.get('id'), currentStartDate=startDate, currentEndDate=endDate, nav=renderedNav())

@app.route("/profile")
@login_is_required
def renderProfile():
    return render_template('profile.html', nav=renderedNav())

##########################################
# Add, Create, and Delete form rendering #
##########################################

@app.route("/form/create-user")
@login_is_required
def renderCreateUser():
    return render_template('create-user.html', nav=renderedNav())

@app.route("/form/create-budget")
@login_is_required
def renderCreateBudget():
    return render_template('create-budget.html', nav=renderedNav())

@app.route("/form/create-earning")
@login_is_required
def renderCreateEarning():
    return render_template('create-earning.html', nav=renderedNav())

@app.route('/form/create-expense')
@login_is_required
def renderCreateExpense():
    categoryInfo = database.getBudgetCategories(session["email"])
    return render_template('create-expense.html', allCategories=categoryInfo, nav=renderedNav())

@app.route("/form/update-user")
@login_is_required
def renderUpdateUser():
    try: 
        databaseInfo = database.getUser(session["email"])["data"]

        return render_template(
            'update-user.html', 
            username=databaseInfo["username"],
            currency=databaseInfo["currency"],
            color=databaseInfo["profileColor"],
            image=databaseInfo["profileImage"],
            nav=renderedNav()
        )
    except Exception as e:
        return custom_error(e)

@app.route("/form/update-budget")
@login_is_required
def renderUpdateBudget():
    try: 
        budgetId = request.args.get("id")
        duplicate = request.args.get("duplicate")

        # This database method checks to make sure that the user owns the budget they are trying to update
        budgetInfo = database.getBudget(budgetId, session["email"])

        if duplicate == "True":
            return render_template(
                'duplicate-budget.html', 
                name=budgetInfo["name"],
                description=budgetInfo["description"],
                amount=budgetInfo["amount"],
                startDate=budgetInfo["startDate"],
                recurPeriod=budgetInfo["budgetPeriod"],
                recurring=budgetInfo["recurring"],
                endDate=budgetInfo["endDate"], 
                nav=renderedNav()
            )
        else:
            currentDate = request.args.get("date")

            return render_template(
                'update-budget.html', 
                id=budgetId,
                currentStartDate=currentDate,
                name=budgetInfo["name"],
                description=budgetInfo["description"],
                amount=budgetInfo["amount"],
                startDate=budgetInfo["startDate"],
                recurPeriod=budgetInfo["budgetPeriod"],
                recurring=budgetInfo["recurring"],
                endDate=budgetInfo["endDate"], 
                nav=renderedNav()
            )
    except Exception as e:
        return custom_error(e)
    
@app.route('/form/update-expense')
@login_is_required
def renderUpdateExpense():
    try:
        expenseId = request.args.get("id")
        duplicate = request.args.get("duplicate")

        # This database method checks to make sure that the user owns the expense they are trying to update
        databaseInfo = database.getExpense(expenseId, session["email"])
        expenseInfo = databaseInfo["data"]
        categoryInfo = databaseInfo["budgetCategories"]

        if duplicate == "True":
            return render_template(
                'duplicate-expense.html', 
                name=expenseInfo["name"], 
                description=expenseInfo["description"], 
                amount=expenseInfo["amount"],
                startDate=expenseInfo["startDate"],
                recurPeriod=expenseInfo["recurPeriod"], 
                recurring=expenseInfo["recurring"],
                category=expenseInfo["budgetCategory"],
                allCategories=categoryInfo,
                endDate=expenseInfo["endDate"], 
                nav=renderedNav()
            )        
        else:
            currentDate = request.args.get("date")

            return render_template(
                'update-expense.html', 
                id=expenseId,
                currentDate=currentDate,           
                name=expenseInfo["name"], 
                description=expenseInfo["description"], 
                amount=expenseInfo["amount"],
                startDate=expenseInfo["startDate"],
                recurPeriod=expenseInfo["recurPeriod"], 
                recurring=expenseInfo["recurring"],
                category=expenseInfo["budgetCategory"],
                allCategories=categoryInfo,
                endDate=expenseInfo["endDate"], 
                nav=renderedNav()
            )
    except Exception as e:
        return custom_error(e)
        
@app.route("/form/update-earning")
@login_is_required
def renderUpdateEarning():
    try: 
        earningId = request.args.get("id")
        duplicate = request.args.get("duplicate")

        # This database method checks to make sure that the user owns the expense they are trying to update
        earningInfo = database.getEarning(earningId, session["email"])

        if duplicate == "True":
                return render_template(
                'duplicate-earning.html', 
                name=earningInfo["name"],
                description=earningInfo["description"],
                amount=earningInfo["amount"],
                startDate=earningInfo["startDate"],
                recurPeriod=earningInfo["recurPeriod"],
                recurring=earningInfo["recurring"],
                endDate=earningInfo["endDate"], 
                nav=renderedNav()
            )
        else:
            currentDate = request.args.get("date")

            return render_template(
                'update-earning.html', 
                id=earningId,
                currentDate=currentDate,
                name=earningInfo["name"],
                description=earningInfo["description"],
                amount=earningInfo["amount"],
                startDate=earningInfo["startDate"],
                recurPeriod=earningInfo["recurPeriod"],
                recurring=earningInfo["recurring"],
                endDate=earningInfo["endDate"], 
                nav=renderedNav()
            )
    except Exception as e:
        return custom_error(e)
    
####################################################
# Routes for getting/updating database information #
####################################################

@app.route("/data/all-current")
@login_is_required
def getAllCurrent():
    try:
        period = request.args.get("period")
        targetDate = request.args.get("target")
        getChartData = True if request.args.get("chartData") and request.args.get("chartData") == "True" else False

        return database.getAllCurrent(session["email"], int(period), str(targetDate), getChartData)
    except Exception as e:
        return custom_error(e)

@app.route("/data/user")
@login_is_required
def getAllUserData():
    return database.getUser(session["email"])

@app.route("/data/budgets")
@login_is_required
def getBudgetData():
    try:
        period = request.args.get("period")
        targetDate = request.args.get("target")

        if period and targetDate:
            return database.getAllActiveBudgets(session["email"], int(period), str(targetDate))
        else:
            return database.getAllActiveBudgets(session["email"])
    except Exception as e:
        return custom_error(e)

@app.route("/data/expenses")
@login_is_required
def getExpenseData():
    try:
        period = request.args.get("period")
        targetDate = request.args.get("target")

        if period and targetDate:
            startDate, endDate = database.getDatesFromPeriod(int(period), str(targetDate))
            return database.getExpensesInRange(session["email"], startDate, endDate)

    except Exception as e:
        return custom_error(e)

@app.route("/data/earnings")
@login_is_required
def getEarningData():
    try:
        period = request.args.get("period")
        targetDate = request.args.get("target")

        if period and targetDate:
            startDate, endDate = database.getDatesFromPeriod(int(period), str(targetDate))
            return database.getEarningsInRange(session["email"], startDate, endDate)

    except Exception as e:
        return custom_error(e)

@app.route("/data/get-budget")
@login_is_required
def getOneBudget():
    budgetId = request.args.get("id")
    date = request.args.get("date")
    if date == None:
        return database.getBudget(budgetId, session["email"])
    else:
        return database.getBudget(budgetId, session["email"], date)
    
@app.route("/data/budget-expenses")
@login_is_required
def getBudgetExpenses():
    try:
        budgetId = request.args.get("id")
        date = request.args.get("date")
        fullExpenses = True if request.args.get("fullExpenses") == "True" else False

        if date == None:
            return database.getBudgetAndExpenses(session["email"], budgetId)
        else:
            return database.getBudgetAndExpenses(session["email"], budgetId, date, fullExpenses)
    except Exception as e:
        return custom_error(e)
    
@app.route("/data/get-expense/")
@login_is_required
def getOneExpense():
    expenseId = request.args.get("id")
    return database.getExpense(expenseId, session["email"])

@app.route("/data/get-earning", methods=['POST'])
@login_is_required
def getOneEarning():
    earningId = request.args.get("id")
    return database.getEarning(earningId, session["email"])

@app.route("/data/create-budget", methods=['POST'])
@login_is_required
def createBudget():
    json_request = request.json
    name = json_request["name"] if bool(json_request["name"]) else ""
    description = json_request["description"] if bool(json_request["description"]) else ""
    amount = json_request["amount"] if bool(json_request["amount"]) else ""
    recurPeriod = json_request["radio"] if bool(json_request["radio"]) else 0
    startDate = json_request["start"] if bool(json_request["start"]) else ""
    endDate = json_request["end"] if bool(json_request["end"]) else ""
    recurring = True if json_request["recurring"] == 'True' else False

    try:
        database.createBudget(
            session["email"], 
            name, 
            startDate,
            endDate,
            amount,
            description, 
            recurring,
            recurPeriod
        )
        return {
            "status": 201,
            "message": "Creation successful!"
        }
    except Exception as e:
        return {
            "status": 400,
            "message": str(e)
        }

@app.route("/data/create-expense", methods=['POST'])
@login_is_required
def createExpense():
    json_request = request.json
    name = json_request["name"] if bool(json_request["name"]) else ""
    amount = json_request["amount"] if bool(json_request["amount"]) else ""
    category = json_request["category"] if bool(json_request["category"]) else ""
    description = json_request["description"] if bool(json_request["description"]) else ""
    recurPeriod = json_request["radio"] if bool(json_request["radio"]) else ""
    startDate = json_request["start"] if bool(json_request["start"]) else ""
    endDate = json_request["end"] if bool(json_request["end"]) else ""
    recurring = True if json_request["recurring"] == 'True' else False
    try:
        database.createExpense(
            session["email"], 
            name,
            category, 
            startDate,
            endDate,
            amount, 
            description, 
            recurPeriod, 
            recurring
        )
        return {
            "status": 201,
            "message": "Creation successful!"
        }
    except Exception as e:
        return {
            "status": 400,
            "message": str(e)
        }
    
@app.route("/data/create-earning", methods=['POST'])
@login_is_required
def createEarning():
    json_request = request.json
    name = json_request["name"] if bool(json_request["name"]) else ""
    amount = json_request["amount"] if bool(json_request["amount"]) else ""
    description = json_request["description"] if bool(json_request["description"]) else ""
    recurPeriod = json_request["radio"] if bool(json_request["radio"]) else ""
    startDate = json_request["start"] if bool(json_request["start"]) else ""
    endDate = json_request["end"] if bool(json_request["end"]) else ""
    recurring = True if json_request["recurring"] == 'True' else False

    try:
        database.createEarning(
            session["email"], 
            name,
            startDate,
            endDate,
            amount, 
            description, 
            recurPeriod, 
            recurring
        )
        return {
            "status": 201,
            "message": "Creation successful!"
        }
    except Exception as e:
        return {
            "status": 400,
            "message": str(e)
        }

@app.route("/data/update-user", methods=['POST'])
@login_is_required
def updateUser():
    json_request = request.json
    username = json_request["username"]
    image = json_request["profileImage"]
    color = json_request["profileColor"]
    currency = json_request["currency"]
    try:
        database.updateUser(
            session["email"], 
            username, 
            image, 
            color,
            currency
        )
        return {
            "status": 201,
            "message": "Update successful!"
        }
    except Exception as e:
        return {
            "status": 400,
            "message": str(e)
        }

@app.route("/data/update-budget", methods=['POST'])
@login_is_required
def updateBudget():
    json_request = request.json
    id = json_request["id"]
    method = json_request["method"] if bool(json_request["method"]) else ""
    name = json_request["name"] if bool(json_request["name"]) else ""
    description = json_request["description"] if bool(json_request["description"]) else ""
    amount = json_request["amount"] if bool(json_request["amount"]) else ""
    budgetPeriod = json_request["radio"] if bool(json_request["radio"]) else 0
    startDate = json_request["start"] if bool(json_request["start"]) else ""
    endDate = json_request["end"] if bool(json_request["end"]) else ""
    currentDate = json_request["current"] if bool(json_request["current"]) else ""
    recurring = True if json_request["recurring"] == 'True' else False
    try:
        database.updateBudget(
            session["email"], 
            id,
            method,
            name,
            startDate,
            endDate, 
            currentDate,
            amount,
            description, 
            budgetPeriod, 
            recurring
        )
        return {
            "status": 201,
            "message": "Update successful!"
        }
    except Exception as e:
        return {
            "status": 400,
            "message": str(e)
        }

@app.route("/data/update-expense", methods=['POST'])
@login_is_required
def updateExpense():
    json_request = request.json
    id = json_request["id"]
    method = json_request["method"] if bool(json_request["method"]) else ""
    name = json_request["name"] if bool(json_request["name"]) else ""
    amount = json_request["amount"] if bool(json_request["amount"]) else ""
    category = json_request["category"] if bool(json_request["category"]) else ""
    description = json_request["description"] if bool(json_request["description"]) else ""
    recurPeriod = json_request["radio"] if bool(json_request["radio"]) else ""
    startDate = json_request["start"] if bool(json_request["start"]) else ""
    endDate = json_request["end"] if bool(json_request["end"]) else ""
    currentDate = json_request["current"] if bool(json_request["current"]) else ""
    recurring = True if json_request["recurring"] == 'True' else False
    
    try:
        database.updateExpense(
            session["email"], 
            id, 
            method,
            name,
            category, 
            startDate,
            endDate,
            currentDate,
            amount, 
            description, 
            recurPeriod, 
            recurring
        )
        return {
            "status": 201,
            "message": "Update successful!"
        }
    except Exception as e:
        return {
            "status": 400,
            "message": str(e)
        }

@app.route("/data/update-earning", methods=['POST'])
@login_is_required
def updateEarning():
    json_request = request.json
    id = json_request["id"]
    method = json_request["method"] if bool(json_request["method"]) else ""
    name = json_request["name"] if bool(json_request["name"]) else ""
    amount = json_request["amount"] if bool(json_request["amount"]) else ""
    description = json_request["description"] if bool(json_request["description"]) else ""
    recurPeriod = json_request["radio"] if bool(json_request["radio"]) else ""
    startDate = json_request["start"] if bool(json_request["start"]) else ""
    endDate = json_request["end"] if bool(json_request["end"]) else ""
    currentDate = json_request["current"] if bool(json_request["current"]) else ""
    recurring = True if json_request["recurring"] == 'True' else False
    
    try:
        database.updateEarning(
            session["email"], 
            id, 
            method,
            name, 
            startDate,
            endDate,
            currentDate,
            amount,
            description, 
            recurPeriod, 
            recurring
        )
        return {
            "status": 201,
            "message": "Update successful!"
        }
    except Exception as e:
        return {
            "status": 400,
            "message": str(e)
        }

##########################################
# Routes for delete database information #
##########################################
@app.route("/data/delete-user", methods=['DELETE'])
@login_is_required
def deleteUser():
    try:
        database.deleteUser(session["email"])
        return {
            "status": 200,
            "message": "Delete successful!"
        }
    except Exception as e:
        return custom_error(e) 

@app.route("/data/delete-budget", methods=['DELETE'])
@login_is_required
def deleteBudget():
    budgetId = request.json["id"]
    method = request.json["method"]
    currentDate = request.json["current"]
    try:
        database.deleteBudget(session["email"], budgetId, method, currentDate)
        return {
            "status": 200,
            "message": "Delete successful!"
        }
    except Exception as e:
        return custom_error(e)

@app.route("/data/delete-expense", methods=['DELETE'])
@login_is_required
def deleteExpense():
    expenseId = request.json["id"]
    method = request.json["method"]
    currentDate = request.json["current"]
    try:
        database.deleteExpense(session["email"], expenseId, method, currentDate)
        return {
            "status": 200,
            "message": "Delete successful!"
        }
    except Exception as e:
        return custom_error(e)

@app.route("/data/delete-earning", methods=['DELETE'])
@login_is_required
def deleteEarning():
    earningId = request.json["id"]
    method = request.json["method"]
    currentDate = request.json["current"]
    try:
        database.deleteEarning(session["email"], earningId, method, currentDate)
        return {
            "status": 200,
            "message": "Delete successful!"
        }
    except Exception as e:
        return custom_error(e)

##########################################################
# Error handling to tell users more helpful information  #
##########################################################

@app.errorhandler(401)
def notLoggedInError(error):
    error=[
        "Wait! You're not logged in yet!",
        "To view this page, you have to first log in. "
    ]
    return render_template('errorPage.html', error=error, loggedIn=isLoggedIn(), nav=renderedNav(), showLogin=True), 404

@app.errorhandler(405)
def unauthorizedAccessAttempt(error):
    error=[
        "You don't have the authority to view this page!",
        "Make sure you are properly logged in to the correct account. "
    ]
    return render_template('errorPage.html', error=error, loggedIn=isLoggedIn(), nav=renderedNav(), showLogin=True), 404

@app.errorhandler(403)
def loginFailed(error):
    error=[
        "Login failed :(",
        "Something went wrong while logging in. Please try again."
    ]
    return render_template('errorPage.html', error=error, loggedIn=isLoggedIn(), nav=renderedNav(), showLogin=True), 404

@app.errorhandler(500)
def page_not_found(error):
    error=[
        "Whoops! That's my fault 😓",
        "The thing you clicked on is broken right now."
    ]
    return render_template('errorPage.html', error=error, loggedIn=isLoggedIn(), nav=renderedNav()), 404

def custom_error(message):
    error=[
        "Something went wrong:",
        message
    ]
    return render_template('errorPage.html', error=error, loggedIn=isLoggedIn(), nav=renderedNav()), 404