import time

import pandas as pd
import psycopg2
from psycopg2 import sql

from utils import *

dbConfig = fileToDictionary("config_db.ini")


def connectToDb(dbConfig):
    connection = psycopg2.connect(**dbConfig)
    return connection


def insertUsers(usersDf):
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    valuesString = ", ".join(
        cursor.mogrify("(%s, %s)", (getattr(user, "username"), getattr(user, "newspageurl"),)).decode("utf-8") for user
        in
        usersDf.itertuples())
    insertUsersSqlQuery = "INSERT INTO newspaper_comments.user (name, newspageurl) VALUES"
    onConflict = "ON CONFLICT (name, newspageurl) DO NOTHING"
    cursor.execute(insertUsersSqlQuery + valuesString + onConflict + ";")
    connection.commit()
    connection.close()


def fetchUsers(newspageUrl):
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM newspaper_comments.user WHERE newspageurl = %s", (newspageUrl,))
    connection.commit()
    users = cursor.fetchall()
    connection.close()
    usersDf = pd.DataFrame(columns=["id", "username", "newspageurl"])
    for user in users:
        newUser = {"id": user[0], "username": user[1], "newspageurl": user[2]}
        usersDf = usersDf._append(newUser, ignore_index=True)
    return usersDf


def fetchAllUsers():
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM newspaper_comments.user")
    connection.commit()
    users = cursor.fetchall()
    connection.close()
    usersDf = pd.DataFrame(columns=["id", "username", "newspageurl"])
    for user in users:
        newUser = {"id": user[0], "username": user[1], "newspageurl": user[2]}
        usersDf = usersDf._append(newUser, ignore_index=True)
    return usersDf


def insertNewsarticle(newsarticleDf):
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    valuesString = ", ".join(cursor.mogrify("(%s, %s, %s, %s)", (getattr(article, "url"),
                                                                 getattr(article, "newspageurl"),
                                                                 time.time(),
                                                                 getattr(article, "isactivelyscraped"),)).decode(
        "utf-8") for article in
                             newsarticleDf.itertuples())
    insertArticleSqlQuery = "INSERT INTO newspaper_comments.newsarticle (url, newspageurl, addedtodb, isactivelyscraped) VALUES"
    onConflictSqlQuery = "ON CONFLICT (url) DO UPDATE SET isactivelyscraped = excluded.isactivelyscraped;"
    cursor.execute(insertArticleSqlQuery + valuesString + onConflictSqlQuery)
    connection.commit()
    connection.close()


def fetchNewsarticle(newspageUrl):
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM newspaper_comments.newsarticle WHERE newspageurl = %s", (newspageUrl,))
    connection.commit()
    newsarticle = cursor.fetchall()
    connection.close()

    newsarticleDf = pd.DataFrame(columns=["url", "newspageurl", "addedtodb"])
    for article in newsarticle:
        newArticle = {"url": article[0], "newspageurl": article[1], "addedtodb": article[2]}
        newsarticleDf = newsarticleDf._append(newArticle, ignore_index=True)
    return newsarticleDf


def fetchAllNewsarticle():
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM newspaper_comments.newsarticle")
    connection.commit()
    newsarticle = cursor.fetchall()
    connection.close()

    newsarticleDf = pd.DataFrame(columns=["url", "newspageurl", "addedToDb"])
    for a in newsarticle:
        article = {"url": a[0], "newspageurl": a[1], "addedToDb": a[2], "isActivelyScraped": a[3]}
        newsarticleDf = newsarticleDf._append(article, ignore_index=True)
    return newsarticleDf


def fetchActivelyScrapedNewsarticle():
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM newspaper_comments.newsarticle where isactivelyscraped = 1")
    connection.commit()
    newsarticle = cursor.fetchall()
    connection.close()

    newsarticleDf = pd.DataFrame(columns=["url", "newspageurl", "addedToDb", "isActivelyScraped"])
    for a in newsarticle:
        article = {"url": a[0], "newspageurl": a[1], "addedToDb": a[2], "isActivelyScraped": a[3]}
        newsarticleDf = newsarticleDf._append(article, ignore_index=True)
    return newsarticleDf


def fetchDateNewestComment(articleUrl):
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    cursor.execute("SELECT max(createdat) FROM newspaper_comments.comment WHERE articleurl = %s", (articleUrl,))
    connection.commit()
    dateNewestComment = cursor.fetchall()
    connection.close()

    return dateNewestComment[0][0]


def insertComments(commentsDf):
    """Adds new comments to the database and or updates the 'deleted' attribute of a comment."""
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    values = []
    for c in commentsDf.itertuples():
        selectUidQuery = psycopg2.extensions.AsIs(
            f"(SELECT id FROM newspaper_comments.user WHERE name = '{getattr(c, 'username')}' AND newspageurl = '{getattr(c, 'newspageurl')}')")
        value = cursor.mogrify("(%s, %s, %s, %s, %s, %s, %s)", (getattr(c, "cid"),
                                                                getattr(c, "parentid"),
                                                                getattr(c, "comment"),
                                                                getattr(c, "timestamp"),
                                                                getattr(c, "articleurl"),
                                                                selectUidQuery,
                                                                getattr(c, "deleted"),
                                                                )).decode("utf-8")
        values.append(value)
    valuesString = ", ".join(values)
    insertCommentsSqlQuery = sql.SQL(
        "INSERT INTO newspaper_comments.comment (id, parentid, text, createdat, articleurl, userid, deleted) VALUES {} ON CONFLICT (id, articleurl) DO UPDATE SET deleted = CASE WHEN excluded.deleted = 1 THEN excluded.deleted ELSE comment.deleted END;")
    fullquery = insertCommentsSqlQuery.format(sql.SQL(valuesString))
    cursor.execute(fullquery)
    connection.commit()
    connection.close()


def updateArticleIsActivelyScraped(articleUrlsFromFile, setting):
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    valuesString = ",".join(cursor.mogrify("(%s)", (url,)).decode("utf-8") for url in articleUrlsFromFile)
    insertCommentsSqlQuery = f"UPDATE newspaper_comments.newsarticle as n SET isActivelyScraped = {setting} FROM (VALUES"
    whereClause = ") AS a(articleUrl) WHERE n.url = a.articleUrl "
    cursor.execute(insertCommentsSqlQuery + valuesString + whereClause)
    connection.commit()
    connection.close()


def insertreactions(reactionsDf):
    """Adds new reactions to the database and or updates attributes of a reaction."""
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    valuesString = ",".join(cursor.mogrify("(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (getattr(r, "cid"),
                                                                                                getattr(r,
                                                                                                        "articleurl"),
                                                                                                getattr(r, "upvotes"),
                                                                                                getattr(r,
                                                                                                        "downvotes"),
                                                                                                getattr(r, "loves"),
                                                                                                getattr(r, "likes"),
                                                                                                getattr(r, "stars"),
                                                                                                getattr(r, "hearts"),
                                                                                                getattr(r, "smiles"),
                                                                                                getattr(r, "frowns"),
                                                                                                getattr(r, "eyebrows"),
                                                                                                getattr(r,
                                                                                                        "astonisheds"),
                                                                                                )).decode("utf-8") for r
                            in
                            reactionsDf.itertuples())
    insertCommentsSqlQuery = "INSERT INTO newspaper_comments.reaction (cid, articleurl, upvotes, downvotes, loves, likes, stars, hearts, smiles, frowns, eyebrows, astonisheds) VALUES"
    onConflict = "ON CONFLICT (cid, articleurl) DO UPDATE SET " \
                 "upvotes = excluded.upvotes," \
                 "downvotes = excluded.downvotes," \
                 "loves = excluded.loves," \
                 "likes = excluded.likes," \
                 "stars = excluded.stars," \
                 "hearts = excluded.hearts," \
                 "smiles = excluded.smiles," \
                 "frowns = excluded.frowns," \
                 "eyebrows = excluded.eyebrows," \
                 "astonisheds = excluded.astonisheds;"

    cursor.execute(insertCommentsSqlQuery + valuesString + onConflict)
    connection.commit()
    connection.close()


def fetchAllComments():
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM newspaper_comments.comment")
    connection.commit()
    comments = cursor.fetchall()
    connection.close()

    commentDf = pd.DataFrame(
        columns=["id", "parentid", "text", "createdat", "articleurl", "userid", "deleted", "upvotes", "downvotes"])
    for c in comments:
        comment = {"id": c[0], "parentid": c[1], "text": c[2], "createdat": c[3], "articleurl": c[4], "userid": c[5],
                   "deleted": c[6], "upvotes": c[7], "downvotes": c[8]}
        commentDf = commentDf._append(comment, ignore_index=True)
    return commentDf


def fetchAllNewspages():
    connection = connectToDb(dbConfig)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM newspaper_comments.newspage")
    connection.commit()
    newspages = cursor.fetchall()
    connection.close()

    newspageDf = pd.DataFrame(columns=["url", "name"])
    for np in newspages:
        newspage = {"url": np[0], "name": np[1]}
        newspageDf = newspageDf._append(newspage, ignore_index=True)
    return newspageDf
