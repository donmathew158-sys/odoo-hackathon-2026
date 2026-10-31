from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    subscription_id = fields.Many2one(
        "brightloop.subscription", string="Subscription",
        copy=False, index=True, ondelete="restrict",
    )
    period_start = fields.Date(copy=False)
    period_end = fields.Date(copy=False)

    _sql_constraints = [
        (
            "brightloop_period_unique",
            "unique(subscription_id, period_start, period_end)",
            "This subscription has already been invoiced for this period.",
        ),
    ]
