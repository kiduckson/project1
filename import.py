from csv import DictReader, reader
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

db_url = "postgres://lezhloywkldvdp:11f1a7a010e6ab980c7b305088022435328a408122b475c7a1bddf66ef7aae41@ec2-3-91-139-25.compute-1.amazonaws.com:5432/dc4aahjhr671tp"

engine = create_engine(db_url)
db = scoped_session(sessionmaker(bind=engine))

db.execute(
    "CREATE TABLE books (id SERIAL PRIMARY KEY, isbn CHAR(10), title TEXT, author TEXT, year NUMERIC)"
)


def main():
    with open("books.csv", 'r') as file:
        reader = DictReader(file)
        for row in reader:
            db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                       {
                           "isbn": row['isbn'],
                           "title": row['title'],
                           "author": row['author'],
                           "year": row['year'],
                       })
        db.commit()


if __name__ == "__main__":
    main()
