from flask import Flask,render_template,url_for,redirect,session,request,flash
app=Flask(__name__)


@app.route('/')
def home():
    return render_template("home.html")

@app.route('/h')
def homee():
    return render_template("check.html")

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
def dashboars():
    return render_template("dashboard.html")

if __name__ =="__main__":
    app.run(debug=True)