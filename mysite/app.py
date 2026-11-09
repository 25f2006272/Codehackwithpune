from flask import Flask,render_template,url_for,redirect,session,request,flash
app=Flask(__name__)


@app.route('/')
def home():
    return render_template("0.html")

@app.route('/h')
def homee():
    return render_template("index.html")

# @app.route('/')
# def home():
#     return render_template("base.html")



if __name__ =="__main__":
    app.run(debug=True)