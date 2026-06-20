IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'policyadmin')
    EXEC('CREATE SCHEMA policyadmin');
GO

IF OBJECT_ID('policyadmin.Coverages') IS NOT NULL DROP TABLE policyadmin.Coverages;
IF OBJECT_ID('policyadmin.Policies')  IS NOT NULL DROP TABLE policyadmin.Policies;
IF OBJECT_ID('policyadmin.Customers') IS NOT NULL DROP TABLE policyadmin.Customers;
GO

CREATE TABLE policyadmin.Customers (
    CustomerID   UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    FirstName    NVARCHAR(100)    NOT NULL,
    LastName     NVARCHAR(100)    NOT NULL,
    DateOfBirth  DATETIME         NOT NULL,
    Email        NVARCHAR(255)    NOT NULL UNIQUE,
    CreatedAt    DATETIME         NOT NULL DEFAULT GETDATE()
);
GO

CREATE TABLE policyadmin.Policies (
    PolicyID           UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    CustomerID         UNIQUEIDENTIFIER NOT NULL REFERENCES policyadmin.Customers(CustomerID),
    PolicyType         NVARCHAR(50)     NOT NULL,
    PremiumAmount      DECIMAL(12,2)    NOT NULL,
    StartDate          DATETIME         NOT NULL,
    EndDate            DATETIME         NOT NULL,
    StatusCode         INT              NOT NULL DEFAULT 1,
    PolicyVersion      INT              NOT NULL DEFAULT 1,
    RenewalOfPolicyID  UNIQUEIDENTIFIER NULL
);
GO

CREATE TABLE policyadmin.Coverages (
    CoverageID     UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
    PolicyID       UNIQUEIDENTIFIER NOT NULL REFERENCES policyadmin.Policies(PolicyID),
    CoverageType   NVARCHAR(100)    NOT NULL,
    CoverageLimit  DECIMAL(14,2)    NOT NULL,
    Deductible     DECIMAL(10,2)    NOT NULL DEFAULT 0.00
);
GO
