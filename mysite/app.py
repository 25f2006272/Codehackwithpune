from flask import Flask,render_template,url_for,redirect,session,request,flash

app=Flask(__name__)


@app.route('/')
def home():
    return render_template("home.html")

# @app.route('/h')
# def homee():
#     return render_template("check.html")

@app.route('/b')
def base():
    return render_template("base.html")

@app.route('/l')
def login():
    return render_template("login.html")


@app.route('/s')
def signup():
    return render_template("signup.html")

@app.route('/d')
def dashboard():
    return render_template("dashboard.html")



@app.route("/overview")
def overview():
    return render_template("overview.html")


@app.route("/activity")
def activity():
    return render_template("activity.html")




@app.route("/projects")
def projects():
    return render_template("projects.html")


@app.route("/tasks")
def tasks():
    return render_template("tasks.html")


@app.route("/handovers")
def handovers():
    return render_template("handovers.html")



@app.route("/library")
def library():
    return render_template("library.html")


@app.route("/review-queue")
def review_queue():
    return render_template("review_queue.html")


@app.route("/ai-insights")
def ai_insights():
    return render_template("ai_insights.html")




@app.route("/workspaces/codehack-team")
def codehack_team():
    return render_template("codehack_team.html")


@app.route("/workspaces/ecometrics")
def ecometrics():
    return render_template("ecometrics.html")


@app.route("/workspaces/research-group")
def research_group():
    return render_template("research_group.html")




@app.route("/setting")
def setting():
    return render_template("settings.html")


@app.route("/help")
def help():
    return render_template("help.html")



@app.route('/logout', methods=["POST"])
def logout():
    return redirect(url_for("login"))


if __name__ =="__main__":
    app.run(debug=True)