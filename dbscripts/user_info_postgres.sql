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

CREATE TABLE IF NOT EXISTS userinfo."Conversation"
(
    "ConversationId"  SERIAL       PRIMARY KEY,
    "UserId"          INT          NOT NULL REFERENCES userinfo."User"("UserId"),
    "SessionId"       VARCHAR(255) NOT NULL UNIQUE,
    "CreatedAt"       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS userinfo."Message"
(
    "MessageId"       SERIAL       PRIMARY KEY,
    "ConversationId"  INT          NOT NULL REFERENCES userinfo."Conversation"("ConversationId"),
    "Role"            VARCHAR(20)  NOT NULL,
    "Content"         TEXT         NOT NULL,
    "CreatedAt"       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO userinfo."User"
("Username", "AppleId", "Email", "FirstName", "LastName")
VALUES ('patpang71', 'patpang71@gmail.com', 'patpang71@gmail.com', 'John', 'Doe')
ON CONFLICT ("Email") DO NOTHING;

INSERT INTO userinfo."Project"
("UserId", "IsDefaultProject", "IsActive", "ProjectName", "JobType", "Description", "StreetAddress", "StreetAddress2", "City", "State", "ZipCode")
SELECT "UserId", TRUE, TRUE, 'Andrea', 'MISC', 'Handyman job', '4735 Andrea Way', '', 'Union City', 'CA', '94587'
FROM userinfo."User"
WHERE "Email" = 'patpang71@gmail.com'
AND NOT EXISTS (
    SELECT 1 FROM userinfo."Project" WHERE "ProjectName" = 'Andrea' AND "UserId" = (
        SELECT "UserId" FROM userinfo."User" WHERE "Email" = 'patpang71@gmail.com'
    )
);
