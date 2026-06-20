IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'claims')
    EXEC('CREATE SCHEMA claims');
GO

IF OBJECT_ID('claims.payouts')      IS NOT NULL DROP TABLE claims.payouts;
IF OBJECT_ID('claims.claim_events') IS NOT NULL DROP TABLE claims.claim_events;
GO

CREATE TABLE claims.claim_events (
    claim_id    INT          IDENTITY(1,1) PRIMARY KEY,
    policy_id   VARCHAR(36)  NOT NULL,
    customer_id INT          NOT NULL,
    event_date  DATE         NOT NULL,
    claim_type  VARCHAR(50)  NOT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'open'
);
GO

CREATE TABLE claims.payouts (
    payout_id     INT           IDENTITY(1,1) PRIMARY KEY,
    claim_id      INT           NOT NULL REFERENCES claims.claim_events(claim_id),
    payout_date   DATE          NOT NULL,
    payout_amount DECIMAL(12,2) NOT NULL,
    is_correction BIT           NOT NULL DEFAULT 0
);
GO
