"""
银行金融业务场景的数据库 Schema 预设
=====================================
为 RAG Code Gen 提供真实银行业务表结构，
让 AI 生成贴合金融场景的 SQL 代码。

使用方法:
  from src.business.banking import HSBC_SCHEMAS
  schema = HSBC_SCHEMAS["customer_risk"]
"""

# ================================================================
#  汇丰银行 (HSBC) 典型业务场景 Schema
# ================================================================

CUSTOMER_ACCOUNTS = """
-- 客户账户主表
CREATE TABLE customers (
    customer_id      BIGINT PRIMARY KEY,
    full_name         VARCHAR(200) NOT NULL,
    id_type           VARCHAR(20) NOT NULL,     -- HKID, PASSPORT, etc.
    id_number         VARCHAR(50) NOT NULL,
    date_of_birth     DATE NOT NULL,
    nationality       VARCHAR(50),
    risk_rating       VARCHAR(10) DEFAULT 'LOW', -- LOW, MEDIUM, HIGH, PROHIBITED
    kyc_status        VARCHAR(20) DEFAULT 'PENDING',
    branch_code       VARCHAR(10),
    relationship_manager VARCHAR(100),
    onboard_date      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_review_date  TIMESTAMP,
    status            VARCHAR(20) DEFAULT 'ACTIVE'
);

-- 账户表
CREATE TABLE accounts (
    account_id        BIGINT PRIMARY KEY,
    customer_id       BIGINT NOT NULL REFERENCES customers(customer_id),
    account_number    VARCHAR(30) NOT NULL UNIQUE,
    account_type      VARCHAR(30) NOT NULL,      -- SAVINGS, CURRENT, FIXED_DEPOSIT, LOAN
    currency          CHAR(3) DEFAULT 'HKD',     -- HKD, USD, CNY, GBP, EUR
    balance           DECIMAL(20,4) DEFAULT 0,
    available_balance DECIMAL(20,4) DEFAULT 0,
    interest_rate     DECIMAL(6,4) DEFAULT 0,
    open_date         DATE NOT NULL,
    maturity_date     DATE,
    status            VARCHAR(20) DEFAULT 'ACTIVE',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 交易流水表
CREATE TABLE transactions (
    transaction_id    BIGINT PRIMARY KEY,
    account_id        BIGINT NOT NULL REFERENCES accounts(account_id),
    transaction_type  VARCHAR(30) NOT NULL,       -- DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT, FEE, INTEREST
    amount            DECIMAL(20,4) NOT NULL,
    currency          CHAR(3) DEFAULT 'HKD',
    counterparty_account VARCHAR(50),
    counterparty_name VARCHAR(200),
    transaction_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    channel           VARCHAR(20),               -- BRANCH, ATM, ONLINE, MOBILE, PHONE
    reference_number  VARCHAR(50),
    description       VARCHAR(500),
    status            VARCHAR(20) DEFAULT 'COMPLETED'
);
"""

RISK_MONITORING = """
-- 风险监控相关表

-- 可疑交易标记
CREATE TABLE suspicious_transactions (
    alert_id          BIGINT PRIMARY KEY,
    transaction_id    BIGINT NOT NULL,
    alert_type        VARCHAR(50) NOT NULL,       -- STRUCTURING, LARGE_CASH, SANCTIONS_HIT, PEP_TRANSACTION
    risk_score        INT CHECK (risk_score BETWEEN 0 AND 100),
    triggered_rules   TEXT,
    review_status     VARCHAR(20) DEFAULT 'PENDING', -- PENDING, UNDER_REVIEW, ESCALATED, CLOSED
    analyst_notes     TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at       TIMESTAMP,
    reviewed_by       VARCHAR(100)
);

-- 大额交易报告
CREATE TABLE large_transaction_reports (
    report_id         BIGINT PRIMARY KEY,
    customer_id       BIGINT NOT NULL,
    account_id        BIGINT NOT NULL,
    transaction_id    BIGINT NOT NULL,
    total_amount      DECIMAL(20,4) NOT NULL,
    currency          CHAR(3),
    report_type       VARCHAR(30),               -- CTR, STR, CROSS_BORDER
    filing_date       DATE NOT NULL,
    regulatory_body   VARCHAR(50),               -- HKMA, JFIU, etc.
    report_status     VARCHAR(20) DEFAULT 'DRAFT',
    submitted_at      TIMESTAMP,
    reference_id      VARCHAR(50)
);

-- 制裁名单筛查
CREATE TABLE sanctions_screening (
    screening_id      BIGINT PRIMARY KEY,
    customer_id       BIGINT NOT NULL,
    match_name        VARCHAR(300),
    match_score       DECIMAL(5,2),
    sanctions_list    VARCHAR(100),              -- OFAC, UN, EU, HK
    screening_date    DATE NOT NULL,
    result            VARCHAR(20) DEFAULT 'CLEAR', -- CLEAR, POTENTIAL_MATCH, CONFIRMED_MATCH
    resolution        VARCHAR(20) DEFAULT 'PENDING',
    resolved_at       TIMESTAMP,
    resolved_by       VARCHAR(100)
);
"""

LOAN_PORTFOLIO = """
-- 贷款组合管理

-- 贷款主表
CREATE TABLE loans (
    loan_id           BIGINT PRIMARY KEY,
    customer_id       BIGINT NOT NULL,
    account_id        BIGINT NOT NULL,
    product_code      VARCHAR(20) NOT NULL,       -- MORTGAGE, PERSONAL, AUTO, SME
    principal_amount  DECIMAL(20,4) NOT NULL,
    outstanding_balance DECIMAL(20,4) NOT NULL,
    interest_rate     DECIMAL(6,4) NOT NULL,
    interest_type     VARCHAR(10) DEFAULT 'FIXED', -- FIXED, FLOATING, HIBOR_LINKED
    start_date        DATE NOT NULL,
    maturity_date     DATE NOT NULL,
    repayment_frequency VARCHAR(10) DEFAULT 'MONTHLY',
    monthly_payment   DECIMAL(20,4),
    collateral_type   VARCHAR(50),
    collateral_value  DECIMAL(20,4),
    ltv_ratio         DECIMAL(5,2),              -- Loan-to-Value
    delinquency_status VARCHAR(20) DEFAULT 'CURRENT', -- CURRENT, 30DPD, 60DPD, 90DPD, NPL
    provision_amount  DECIMAL(20,4) DEFAULT 0,
    last_payment_date DATE,
    next_payment_date DATE,
    status            VARCHAR(20) DEFAULT 'ACTIVE'
);

-- 还款记录
CREATE TABLE loan_repayments (
    repayment_id      BIGINT PRIMARY KEY,
    loan_id           BIGINT NOT NULL REFERENCES loans(loan_id),
    due_date          DATE NOT NULL,
    payment_date      DATE,
    scheduled_amount  DECIMAL(20,4) NOT NULL,
    paid_amount       DECIMAL(20,4) DEFAULT 0,
    outstanding_after DECIMAL(20,4),
    days_late         INT DEFAULT 0,
    payment_method    VARCHAR(20),
    status            VARCHAR(20) DEFAULT 'PENDING' -- PENDING, PARTIAL, COMPLETE, OVERDUE
);
"""

TRADE_FINANCE = """
-- 贸易融资相关表

-- 信用证 (Letter of Credit)
CREATE TABLE letters_of_credit (
    lc_id             BIGINT PRIMARY KEY,
    lc_number         VARCHAR(50) UNIQUE NOT NULL,
    applicant_id      BIGINT NOT NULL,            -- 申请人 (进口商)
    beneficiary_id    BIGINT NOT NULL,            -- 受益人 (出口商)
    issuing_bank      VARCHAR(100) NOT NULL,
    advising_bank     VARCHAR(100),
    lc_type           VARCHAR(20),               -- SIGHT, USANCE, STANDBY, REVOLVING
    amount            DECIMAL(20,4) NOT NULL,
    currency          CHAR(3) DEFAULT 'USD',
    issue_date        DATE NOT NULL,
    expiry_date       DATE NOT NULL,
    latest_ship_date  DATE,
    goods_description TEXT,
    port_of_loading   VARCHAR(100),
    port_of_discharge VARCHAR(100),
    documents_required TEXT,
    status            VARCHAR(20) DEFAULT 'ISSUED', -- ISSUED, AMENDED, PRESENTED, SETTLED, EXPIRED
    settled_amount    DECIMAL(20,4) DEFAULT 0,
    settlement_date   DATE
);

-- 贸易融资额度
CREATE TABLE trade_finance_limits (
    limit_id          BIGINT PRIMARY KEY,
    customer_id       BIGINT NOT NULL,
    facility_type     VARCHAR(50) NOT NULL,        -- LC_ISSUANCE, TRUST_RECEIPT, PACKING_CREDIT, FORFAITING
    total_limit       DECIMAL(20,4) NOT NULL,
    utilized_amount   DECIMAL(20,4) DEFAULT 0,
    available_amount  DECIMAL(20,4) NOT NULL,
    currency          CHAR(3),
    start_date        DATE NOT NULL,
    expiry_date       DATE NOT NULL,
    review_date       DATE,
    status            VARCHAR(20) DEFAULT 'ACTIVE'
);
"""

HSBC_SCHEMAS = {
    "customer_accounts": CUSTOMER_ACCOUNTS,
    "risk_monitoring": RISK_MONITORING,
    "loan_portfolio": LOAN_PORTFOLIO,
    "trade_finance": TRADE_FINANCE,
}

HSBC_DESCRIPTIONS = {
    "customer_accounts": "客户账户管理 - customers, accounts, transactions",
    "risk_monitoring": "风险监控 - 可疑交易、大额报告、制裁筛查",
    "loan_portfolio": "贷款组合 - 贷款主表、还款记录",
    "trade_finance": "贸易融资 - 信用证、贸易额度",
}


def get_schema(scenario: str) -> str:
    """获取指定场景的完整 Schema"""
    return HSBC_SCHEMAS.get(scenario, "")


def list_scenarios() -> dict[str, str]:
    """列出所有可用场景"""
    return HSBC_DESCRIPTIONS


def get_full_bank_schema() -> str:
    """获取全部银行 Schema 的组合"""
    return "\n\n".join(HSBC_SCHEMAS.values())
