# Brightloop Subscription Management (Odoo x Make-A-Ton 9.0)

Replaces Brightloop's spreadsheets with one Odoo 18 platform for plans, quotations,
subscriptions, recurring invoicing, taxes, discounts, payments, a finance dashboard and a customer portal.

## Features
- Plans with interval, minimum quantity and rules (pause, early close, renew, auto close)
- Subscriptions with a validated lifecycle: draft, quotation, confirmed, active, paused, closed
- Lines with taxes (Odoo tax engine) and discounts; History audit trail
- Quotation templates that pre-fill plan and lines
- Recurring billing: daily cron plus a Run Billing button, catch-up for missed periods,
  row locking and a database unique constraint (subscription, period) so no double billing
- Native Odoo invoices and PDF; payment tracking (invoiced, paid, due) and overdue detection
- Finance dashboard: billed revenue, monthly recurring revenue, overdue
- Customer portal at /my/subscriptions (view, invoices, pause, resume, close)
- Password policy: minimum 10 characters
- Automated tests

## Run it
1. Install Docker Desktop.
2. Copy `.env.example` to `.env` and set your own passwords (never commit `.env`).
3. `docker compose up -d`, then open http://localhost:8069
4. Install the app "Brightloop Subscription Management".

## Upgrade after code changes
    docker compose exec odoo bash -c 'odoo -d brightloop -u brightloop_subscription --stop-after-init --db_host=$HOST --db_user=$USER --db_password=$PASSWORD'
    docker compose restart odoo

## Run the tests
    docker compose exec odoo bash -c 'odoo -d brightloop -u brightloop_subscription --test-tags /brightloop_subscription --stop-after-init --db_host=$HOST --db_user=$USER --db_password=$PASSWORD'

## Roles
- Brightloop Administrator: everything, including the dashboard
- Brightloop Staff: create and edit subscriptions, read plans and templates
- Portal customer: own subscriptions and invoices only