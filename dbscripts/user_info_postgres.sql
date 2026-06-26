CREATE SCHEMA IF NOT EXISTS userinfo;

CREATE TABLE IF NOT EXISTS userinfo."User"
(
    "UserId"      SERIAL       PRIMARY KEY,
    "Username"    VARCHAR(50)  NOT NULL,
    "AppleId"     VARCHAR(255) UNIQUE,
    "GoogleId"    VARCHAR(255) UNIQUE,
    "AvatarUrl"   VARCHAR(500),
    "Email"       VARCHAR(100) NOT NULL UNIQUE,
    "FirstName"   VARCHAR(50),
    "LastName"    VARCHAR(50),
    "CreatedAt"   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS userinfo."Project"
(
    "ProjectId"        SERIAL       PRIMARY KEY,
    "UserId"           INT          NOT NULL REFERENCES userinfo."User"("UserId"),
    "IsDefaultProject" BOOLEAN      NOT NULL DEFAULT FALSE,
    "IsActive"         BOOLEAN      NOT NULL DEFAULT TRUE,
    "ProjectName"      VARCHAR(100) NOT NULL,
    "JobType"          VARCHAR(50)  NOT NULL,
    "Description"      VARCHAR(255),
    "StreetAddress"    VARCHAR(255),
    "StreetAddress2"   VARCHAR(255),
    "City"             VARCHAR(100),
    "State"            VARCHAR(50),
    "ZipCode"          VARCHAR(20),
    "CreatedAt"        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
