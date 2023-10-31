CREATE TABLE newspaper_comments.newspage
(
    url  text PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE newspaper_comments.newsarticle
(
    url               text PRIMARY KEY,
    newspageUrl       text,
    addedToDb         bigint,
    isActivelyScraped int,
    FOREIGN KEY (newspageUrl)
        REFERENCES newspaper_comments.newspage (url)
);

CREATE TABLE newspaper_comments.user
(
    id          SERIAL PRIMARY KEY,
    name        text NOT NULL,
    newspageUrl text,
    UNIQUE (name, newspageUrl),
    FOREIGN KEY (newspageUrl)
        REFERENCES newspaper_comments.newspage (url)
);

CREATE TABLE newspaper_comments.comment
(
    id         text,
    parentId   text,
    text       text,
    createdAt  bigint,
    articleUrl text,
    userId     integer,
    deleted    integer,
    PRIMARY KEY (id, articleUrl),
    FOREIGN KEY (articleUrl)
        REFERENCES newspaper_comments.newsarticle (url),
    FOREIGN KEY (userId)
        REFERENCES newspaper_comments.user (id)
);

CREATE TABLE newspaper_comments.reaction
(
    cid         text,
    articleUrl  text,
    upvotes     integer,
    downvotes   integer,
    loves       integer,
    likes       integer,
    stars       integer,
    hearts      integer,
    smiles      integer,
    frowns      integer,
    eyebrows    integer,
    astonisheds integer,
    PRIMARY KEY (cid, articleUrl),
    FOREIGN KEY (cid, articleUrl)
        REFERENCES newspaper_comments.comment (id, articleUrl)
);
