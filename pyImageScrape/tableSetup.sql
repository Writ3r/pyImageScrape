CREATE TABLE IF NOT EXISTS urls (
    urlLoc VARCHAR(100) PRIMARY KEY NOT NULL,
    visited INTEGER
);

CREATE TABLE IF NOT EXISTS picUrls (
    urlLoc VARCHAR(100) PRIMARY KEY NOT NULL,
    visited INTEGER
);
