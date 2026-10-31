# Brightloop Subscription Management

**An all-in-one subscription management and recurring billing platform built with Odoo 18.**

Developed for **Odoo x Make-A-Ton 9.0**.

## Overview

Brightloop Subscription Management replaces scattered spreadsheets and manual billing workflows with a centralized platform for managing subscription businesses.

It brings subscription plans, customer quotations, subscription lifecycles, recurring invoices, payment tracking, and financial reporting together in one Odoo 18 application.

## Key Features

### 1. Subscription Plan Management
- Create monthly and yearly subscription plans.
- Configure pricing and billing intervals.
- Set minimum quantities and subscription rules.
- Configure pause, renewal, early closure, and automatic closure policies.

### 2. Complete Subscription Lifecycle
Manage subscriptions through a controlled lifecycle:

`Draft → Quotation → Confirmed → Active → Paused / Closed`

- Generate quotations from subscription plans.
- Confirm orders and activate subscriptions.
- Track subscription status and history.
- Maintain an audit trail of changes.

### 3. Automated Recurring Billing
- Generate recurring invoices automatically.
- Daily scheduled billing through Odoo Cron.
- Manual billing through the Run Billing button.
- Catch up on missed billing periods.
- Database-level duplicate billing protection using row locking and unique constraints.

### 4. Invoices and Payments
- Native Odoo accounting invoices.
- Integrated Odoo tax engine.
- Discounts and invoice line management.
- Paid, outstanding, and overdue invoice tracking.
- PDF invoice generation.

### 5. Finance Dashboard
A centralized dashboard providing financial visibility:

- Billed revenue.
- Monthly Recurring Revenue (MRR).
- Outstanding invoices.
- Overdue payments.
- Interactive financial reporting.

### 6. Customer Portal
Customers can access their subscriptions through:

`/my/subscriptions`

Portal functionality:
- View their subscriptions.
- Access related invoices.
- Request subscription pauses.
- Resume subscriptions.
- Request subscription closure.

### 7. Security and Reliability
- Role-based access control.
- Customer-specific portal access.
- Password policy requiring at least 10 characters.
- Subscription lifecycle validation.
- Duplicate invoice prevention.
- Automated tests.

## Technology Stack

| Technology | Purpose |
|---|---|
| Odoo 18 | Business application framework |
| Python | Backend business logic |
| PostgreSQL | Database |
| XML | Odoo views and UI |
| JavaScript | Frontend functionality |
| Docker | Development environment |
| Odoo Accounting | Invoices, taxes and payments |

## Installation and Setup

### Requirements
- Docker Desktop
- Git

### 1. Clone the repository

```bash
git clone https://github.com/donmathew158-sys/odoo-hackathon-2026.git
cd odoo-hackathon-2026
```

### 2. Configure environment variables

Copy the example environment file:

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
```

Open `.env` and configure your own database credentials.

Never commit your actual `.env` file.

### 3. Start the application

```bash
docker compose up -d
```

### 4. Open Odoo

Visit:

http://localhost:8069

Install the application:

**Brightloop Subscription Management**

## Upgrade After Code Changes

```bash
docker compose exec odoo bash -c 'odoo -d brightloop -u brightloop_subscription --stop-after-init --db_host=$HOST --db_user=$USER --db_password=$PASSWORD'
docker compose restart odoo
```

## Run Automated Tests

```bash
docker compose exec odoo bash -c 'odoo -d brightloop -u brightloop_subscription --test-tags /brightloop_subscription --stop-after-init --db_host=$HOST --db_user=$USER --db_password=$PASSWORD'
```

## User Roles

| Role | Permissions |
|---|---|
| Brightloop Administrator | Full system access and financial dashboard |
| Brightloop Staff | Create and edit subscriptions; read plans and templates |
| Portal Customer | Access their own subscriptions and invoices |

## Project Repository

GitHub: https://github.com/donmathew158-sys/odoo-hackathon-2026

---

**Brightloop Subscription Management — Simplifying subscriptions, automating billing, and improving financial visibility.**

*Built for Odoo x Make-A-Ton 9.0.*
