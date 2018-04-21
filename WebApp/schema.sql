CREATE DATABASE fitbit;
USE fitbit;

-- CREATE USER TABLE FOR EACH USER
CREATE TABLE USER (
    FBID CHAR(6) NOT NULL,
    ACCESS_TOKEN VARCHAR(1024),
    REFRESH_TOKEN VARCHAR(1024),
    NAME VARCHAR(50),
    LOCATION VARCHAR(20),
    -- GENDER VARCHAR(6),
    -- EMAIL VARCHAR(40),
    -- DOB DATE
    PRIMARY KEY (FBID)
);

-- CREATE ACTIVITIES TABLE TO HOLD USERS FITBIT ACTIVITY QUEUE
CREATE TABLE ACTIVITIES(
    FBID CHAR(6) NOT NULL,
    -- DATE DATE,
    -- TIME TIME,
    ACTIVITY VARCHAR(40),
    PRIMARY KEY (FBID, ACTIVITY),
    FOREIGN KEY (FBID) REFERENCES USER(FBID) ON DELETE CASCADE
);

-- CREATE CACHE TABLE TO HOLD USERS MOST RECENT SEARCH THROUGH THE WEBAPP
CREATE TABLE RESULTCACHE(
    SID CHAR(40) NOT NULL,
    NAME VARCHAR(150),
    DATE VARCHAR(40),
    VENUE VARCHAR(100),
    DES VARCHAR(5000),
    LINK VARCHAR(150) NOT NULL,
    RNUM INT,
    PRIMARY KEY (SID, LINK)
);

-- CREATE SAVEDEVENTS TABLE TO HOLD SAVED USERS EVENTS
CREATE TABLE SAVEDEVENTS(
    FBID CHAR(6) NOT NULL,
    SID VARCHAR(40),
    NAME VARCHAR(150),
    DATE VARCHAR(40),
    VENUE VARCHAR(100),
    DES VARCHAR(5000),
    LINK VARCHAR(150),
    PRIMARY KEY (FBID),
    FOREIGN KEY (FBID) REFERENCES USER(FBID) ON DELETE CASCADE
);

CREATE TABLE RECOMMENDATIONS(
    NAME VARCHAR(150),
    DATE VARCHAR(40),
    VENUE VARCHAR(100),
    DES VARCHAR(5000),
    LINK VARCHAR(150),
    RNUM INT,
    PRIMARY KEY (RNUM)
);