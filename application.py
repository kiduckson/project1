import os

from flask import Flask, session, jsonify, redirect, render_template, request, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from utils import login_required, api_call


app = Flask(__name__)

db_url = "postgres://lezhloywkldvdp:11f1a7a010e6ab980c7b305088022435328a408122b475c7a1bddf66ef7aae41@ec2-3-91-139-25.compute-1.amazonaws.com:5432/dc4aahjhr671tp"

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(db_url)
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if session.get("user_id") is None:
        return render_template("login.html")
    return render_template("search.html")


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    if request.method == "GET":
        return render_template("search.html")

    else:
        search = request.form.get("search")
        qstr = "%{}%".format(search.lower())

        if not search:
            return render_template("search.html", error="Please enter a word")

        # search result
        results = db.execute(
            "SELECT * FROM books WHERE lower(title) LIKE :search OR lower(author) LIKE :search OR lower(isbn) LIKE :search", {"search": qstr}).fetchall()

        if results == []:
            return render_template("search.html", error="No such book")

        return render_template("search.html", results=results)


@app.route("/book/<int:book_id>", methods={"GET", "POST"})
@login_required
def book(book_id):
    # create review table is not exist
    db.execute(
        "CREATE TABLE IF NOT EXISTS reviews (id SERIAL PRIMARY KEY, rating INT, content TEXT, book_id INT, user_id INT, time TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(book_id) REFERENCES books(id))")

    # get the user id
    user_id = session['user_id']

    # query the db
    book = db.execute("SELECT * FROM books WHERE id= :id",
                      {"id": book_id}).fetchone()

    # fetch the required data from the Goodread Api
    result = api_call(book['isbn'])

    # fetch the reviews from the db
    reviews = db.execute(
        "SELECT username, rating, content, time FROM reviews JOIN users ON reviews.user_id = users.id WHERE book_id= :book_id ORDER BY time DESC",
        {"book_id": book_id}).fetchall()

    # get the book data
    if request.method == "GET":

        # if book does not exist
        if book is None:
            return render_template("search.html", error="No such book exist.")

        # if there is no review yet been posted.
        if reviews is None:
            return render_template("book.html", book=book, result=result)

        # render all
        return render_template("book.html", book=book, result=result, reviews=reviews)

    # post
    else:
        # create review table is not exist
        db.execute(
            "CREATE TABLE IF NOT EXISTS reviews (id SERIAL PRIMARY KEY, rating INT, content TEXT, book_id INT, user_id INT, time TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(book_id) REFERENCES books(id))")

        if not request.form.get("rating_score"):
            return render_template("book.html", book=book, result=result, reviews=reviews, error="Please rate the book")

        # review contents
        content = request.form.get("content")
        rating = int(request.form.get("rating_score"))

        print(rating)

        db.execute("INSERT INTO reviews (rating, content, book_id, user_id, time) VALUES (:rating, :content, :book_id, :user_id, CURRENT_TIMESTAMP)", {
                   "rating": rating, "content": content, "book_id": book_id, "user_id": user_id})

        # commit to the db
        db.commit()

        # fetch the reviews from the db
        reviews = db.execute(
            "SELECT username, rating, content, time FROM reviews JOIN users ON reviews.user_id = users.id WHERE book_id= :book_id ORDER BY time DESC",
            {"book_id": book_id}).fetchall()

        return render_template("book.html", book=book, result=result, reviews=reviews)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    # get user input
    username = request.form.get("username")
    password = request.form.get("password")
    re = request.form.get("re")

    # if no username given
    if not username:
        return render_template("register.html", error="Please enter a username")

    # if pw is too short
    if len(password) < 6:
        return render_template("register.html", error="Password must be longer than 6 characters")

    # if pw not match
    if re != password:
        return render_template("register.html", error="Passwords must match")

    # hash the pw
    hashed_pw = generate_password_hash(password)

    # create a user table if not exist
    db.execute(
        "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT, hash TEXT)")

    # check duplicate
    rows = db.execute(
        "SELECT * FROM users WHERE username = :username", {"username": username}).fetchall()
    if len(rows) == 1:
        return render_template("register.html", error="{} is taken".format(username))

    # insert the user into the table
    db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)",
               {"username": username, "password": hashed_pw})

    # commit
    db.commit()

    return render_template("login.html", error="Registration was successful!")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    else:
        session.clear()

        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return render_template("login.html", error="Please enter a username")
        elif not password:
            return render_template("login.html", error="Please enter a password")

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": request.form.get("username")}).fetchall()

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("login.html", error="Password does not match")

        session["user_id"] = rows[0]["id"]

        return render_template("search.html", error="Login was successful!")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/api/<path:isbn>")
def book_api(isbn):

    print(isbn)

    data = db.execute(
        "SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    if data is None:
        return jsonify({"error": "Invalid isbn"}), 422

    res = db.execute("SELECT AVG(rating) as review_count, COUNT(id) as average_score FROM reviews WHERE book_id = :book_id", {
                     "book_id": data['id']}).fetchone()

    print(data['title'])
    print(res['review_count'])
    print(res['average_score'])

    return jsonify({
        "title": data['title'],
        "author": data['author'],
        "year": int(data['year']),
        "isbn": data['isbn'],
        'review_count': res['review_count'] if res['review_count'] else 0,
        'average_score': res['average_score'] if res['average_score'] else 0,
    })
