CREATE SCHEMA IF NOT EXISTS userinfo;

CREATE TABLE IF NOT EXISTS userinfo."User"
(
    "UserId"      SERIAL       PRIMARY KEY,
    "AppleId"     VARCHAR(255) UNIQUE,
    "GoogleId"    VARCHAR(255) UNIQUE,
    "AvatarUrl"   VARCHAR(500),
    "Email"       VARCHAR(100) NOT NULL UNIQUE,
    "FirstName"   VARCHAR(50),
    "LastName"    VARCHAR(50),
    "Preference"  VARCHAR(10)  NOT NULL DEFAULT 'CONCISE'
                  CHECK ("Preference" IN ('CONCISE', 'DETAIL')),
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
    "ResolutionDetail" VARCHAR(255),
    "Resolved"         BOOLEAN      NOT NULL DEFAULT FALSE,
    "CreatedAt"        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS userinfo."SearchResult"
(
    "SearchResultId"  SERIAL       PRIMARY KEY,
    "ProjectId"       INT          NOT NULL REFERENCES userinfo."Project"("ProjectId"),
    "SearchQuestion"  TEXT         NOT NULL,
    "SearchResult"    TEXT         NOT NULL,
    "CreatedAt"       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
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

-- Migration guard: CREATE TABLE IF NOT EXISTS above no-ops on tables that already
-- exist, so column changes to already-provisioned tables must be applied here,
-- idempotently, on every run.
ALTER TABLE userinfo."User" DROP COLUMN IF EXISTS "Username";
ALTER TABLE userinfo."User" ADD COLUMN IF NOT EXISTS "Preference" VARCHAR(10) NOT NULL DEFAULT 'CONCISE'
    CHECK ("Preference" IN ('CONCISE', 'DETAIL'));

ALTER TABLE userinfo."Project" ADD COLUMN IF NOT EXISTS "ResolutionDetail" VARCHAR(255);
ALTER TABLE userinfo."Project" ADD COLUMN IF NOT EXISTS "Resolved" BOOLEAN NOT NULL DEFAULT FALSE;

INSERT INTO userinfo."User"
("AppleId", "Email", "FirstName", "LastName")
VALUES ('patpang71@gmail.com', 'patpang71@gmail.com', 'John', 'Doe')
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
