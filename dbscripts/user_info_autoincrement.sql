DROP DATABASE IF EXISTS `UserInfo_AutoIncrement`;

CREATE DATABASE `UserInfo_AutoIncrement`;

USE `UserInfo_AutoIncrement`;

/*******************************************************************************
   Create Tables
********************************************************************************/
CREATE TABLE `User`
(
    `UserId` INT NOT NULL AUTO_INCREMENT,
    `Username` NVARCHAR(50) NOT NULL,
    `Email` NVARCHAR(100) NOT NULL,
    `FirstName` NVARCHAR(50) NOT NULL,
    `LastName` NVARCHAR(50) NOT NULL,
    CONSTRAINT `PK_User` PRIMARY KEY  (`UserId`)
);

CREATE TABLE `Project`
(
    `ProjectId` INT NOT NULL AUTO_INCREMENT,
    `UserId` INT NOT NULL,
    `IsDefaultProject` BIT NOT NULL DEFAULT 0,
    `IsActive` BIT NOT NULL DEFAULT 1,
    `ProjectName` NVARCHAR(100) NOT NULL,
    `JobType` NVARCHAR(50) NOT NULL,
    `Description` NVARCHAR(255),
    `CreatedDate` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `StreetAddress` NVARCHAR(255),
    `StreetAddress2` NVARCHAR(255),
    `City` NVARCHAR(100),
    `State` NVARCHAR(50),
    `ZipCode` NVARCHAR(20),
    CONSTRAINT `PK_Project` PRIMARY KEY  (`ProjectId`)
);


