from flask import Blueprint

auth = Blueprint("auth", __name__)

@auth.route("/login/google")
def login_google():
    # Googleログインのロジック
    pass

@auth.route("/login/twitter")
def login_twitter():
    # Twitterログインのロジック
    pass
