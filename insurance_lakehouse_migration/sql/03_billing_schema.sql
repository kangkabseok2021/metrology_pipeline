IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'billing')
    EXEC('CREATE SCHEMA billing');
GO

IF OBJECT_ID('billing.payments') IS NOT NULL DROP TABLE billing.payments;
IF OBJECT_ID('billing.invoices') IS NOT NULL DROP TABLE billing.invoices;
GO

CREATE TABLE billing.invoices (
    invoice_id     INT           IDENTITY(1,1) PRIMARY KEY,
    policy_id      VARCHAR(36)   NOT NULL,
    customer_email NVARCHAR(255) NULL,
    invoice_date   VARCHAR(10)   NOT NULL,
    due_date       VARCHAR(10)   NOT NULL,
    amount         DECIMAL(12,2) NOT NULL,
    currency       VARCHAR(3)    NOT NULL DEFAULT 'EUR'
);
GO

CREATE TABLE billing.payments (
    payment_id     INT           IDENTITY(1,1) PRIMARY KEY,
    invoice_id     INT           NOT NULL REFERENCES billing.invoices(invoice_id),
    payment_date   VARCHAR(10)   NOT NULL,
    amount_paid    DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(30)   NOT NULL
);
GO
