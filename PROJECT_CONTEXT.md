# Project Context

- Stack: Odoo 18, Postgres 16, Docker Compose, module `addons/brightloop_subscription`
- Decision: reuse native Odoo models (account.move, res.partner, product.product, taxes)
- Decision: taxes via `compute_all`; amounts in Monetary fields
- Decision: duplicate invoices prevented by SQL unique(subscription_id, period_start, period_end) and `FOR UPDATE SKIP LOCKED`
- Decision: state changes only through workflow buttons (context guard `bl_state_change`)
- Decision: portal controllers use sudo with an explicit customer domain
- Assumption: a native Odoo module is allowed by the hackathon rules (unconfirmed)
- Windows note: write files without a BOM (a BOM breaks `__manifest__.py`)