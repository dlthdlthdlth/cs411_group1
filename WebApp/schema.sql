CREATE DATABASE fitbit;
USE fitbit;

-- CREATE USER TABLE FOR EACH USER
CREATE TABLE USER (
    UID INT NOT NULL AUTO_INCREMENT,
    GENDER VARCHAR(6),
    EMAIL VARCHAR(40),
    DOB DATE,
    FBID INT,
    HOMETOWN VARCHAR(40),
    FNAME VARCHAR(40),
    LNAME VARCHAR(40),
    PRIMARY KEY (UID)
);

-- CREATE FITBIT TABLE TO HOLD USERS FITBIT ACTIVITY QUEUE
CREATE TABLE FITBIT(
    UID INT NOT NULL,
    FBID INT NOT NUll,
    DATE DATE,
    TIME TIME,
    ACTIVITY VARCHAR(40),
    PRIMARY KEY (UID, FBID),
    FOREIGN KEY (UID) REFERENCES USER(UID) ON DELETE CASCADE
);

-- CREATE PASTEVENT TABLE TO HOLD USERS PAST ACTIVITY THROUGH THE WEBAPP (PAST TICKETBRITE EVENTS)
CREATE TABLE PASTEVENTS(
    UID INT NOT NULL,
    DATE DATE,
    TIME TIME,
    LOCATION VARCHAR(40),
    ENAME VARCHAR(40),
    TYPE VARCHAR(40),
    INFO VARCHAR(100),
    PRIMARY KEY (UID),
    FOREIGN KEY (UID) REFERENCES USER(UID) ON DELETE CASCADE
);

-- CREATE FUTUREEVENT TABLE TO HOLD EVENTS USERS ARE REGISTERED FOR
CREATE TABLE FUTUREEVENTS(
    UID INT NOT NULL,
    DATE DATE,
    TIME TIME,
    LOCATION VARCHAR(40),
    ENAME VARCHAR(40),
    TYPE VARCHAR(40),
    INFO VARCHAR(100),
    PRIMARY KEY (UID),
    FOREIGN KEY (UID) REFERENCES USER(UID) ON DELETE CASCADE
);

-- CREATE SAVEDEVENTS TABLE TO HOLD SAVED USERS EVENTS
CREATE TABLE SAVEDEVENTS(
    UID INT NOT NULL,
    DATE DATE,
    TIME TIME,
    LOCATION VARCHAR(40),
    ENAME VARCHAR(40),
    TYPE VARCHAR(40),
    INFO VARCHAR(100),
    PRIMARY KEY (UID),
    FOREIGN KEY (UID) REFERENCES USER(UID) ON DELETE CASCADE
);