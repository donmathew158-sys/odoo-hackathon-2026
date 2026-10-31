import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from .subscription import INTERVAL_DELTA

_logger = logging.getLogger(__name__)


class BrightloopSubscriptionBilling(models.Model):
    _inherit = "brightloop.subscription"

    invoice_ids = fields.One2many("account.move", "subscription_id", string="Invoices")
    invoice_count = fields.Integer(compute="_compute_invoice_count")
    is_overdue = fields.Boolean(
        compute="_compute_is_overdue", search="_search_is_overdue", string="Overdue"
    )

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.sudo().invoice_ids)

    def _overdue_domain(self):
        today = fields.Date.context_today(self)
        return [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["not_paid", "partial"]),
            ("invoice_date_due", "<", today),
        ]

    def _compute_is_overdue(self):
        overdue = self.env["account.move"].sudo().search(
            self._overdue_domain() + [("subscription_id", "in", self.ids)]
        ).mapped("subscription_id").ids
        for rec in self:
            rec.is_overdue = rec.id in overdue

    def _search_is_overdue(self, operator, value):
        moves = self.env["account.move"].sudo().search(
            self._overdue_domain() + [("subscription_id", "!=", False)]
        )
        ids = moves.mapped("subscription_id").ids
        positive = (operator == "=" and value) or (operator == "!=" and not value)
        return [("id", "in" if positive else "not in", ids)]

    def _get_period(self):
        self.ensure_one()
        start = self.next_billing_date
        delta = relativedelta(**INTERVAL_DELTA[self.plan_id.interval])
        end = start + delta - relativedelta(days=1)
        return start, end

    def _prepare_invoice_vals(self, start, end):
        self.ensure_one()
        lines = []
        for line in self.line_ids:
            lines.append((0, 0, {
                "product_id": line.product_id.id,
                "name": "%s (%s to %s)" % (line.product_id.display_name, start, end),
                "quantity": line.quantity,
                "price_unit": line.unit_price,
                "tax_ids": [(6, 0, line.tax_ids.ids)],
            }))
        return {
            "move_type": "out_invoice",
            "partner_id": self.customer_id.id,
            "currency_id": self.currency_id.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_payment_term_id": self.payment_term_id.id,
            "invoice_origin": self.name,
            "subscription_id": self.id,
            "period_start": start,
            "period_end": end,
            "invoice_line_ids": lines,
        }

    def _bill_one(self):
        """Bill one period for one subscription. Returns the invoice id or False."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        self.env.cr.execute(
            "SELECT id FROM brightloop_subscription WHERE id = %s FOR UPDATE SKIP LOCKED",
            (self.id,),
        )
        if not self.env.cr.fetchone():
            return False
        self.invalidate_recordset()
        if self.state != "active" or not self.next_billing_date:
            return False
        if self.next_billing_date > today or not self.line_ids:
            return False
        start, end = self._get_period()
        if self.expiry_date and start > self.expiry_date:
            if self.plan_id.auto_close:
                self._change_state("closed")
            return False
        Move = self.env["account.move"].sudo()
        invoice = Move.search([
            ("subscription_id", "=", self.id),
            ("period_start", "=", start),
            ("period_end", "=", end),
        ], limit=1)
        if not invoice:
            invoice = Move.create(self._prepare_invoice_vals(start, end))
            invoice.action_post()
        delta = relativedelta(**INTERVAL_DELTA[self.plan_id.interval])
        self.next_billing_date = start + delta
        self._log("active", "active", "Invoiced %s: %s to %s" % (invoice.name, start, end))
        return invoice.id

    def _bill_due(self):
        created = []
        for sub in self:
            for _ in range(24):
                try:
                    with self.env.cr.savepoint():
                        invoice_id = sub._bill_one()
                except Exception:
                    _logger.exception("Billing failed for subscription %s", sub.name)
                    break
                if not invoice_id:
                    break
                created.append(invoice_id)
        return created

    @api.model
    def _cron_run_billing(self):
        today = fields.Date.context_today(self)
        subs = self.search([
            ("state", "=", "active"),
            ("next_billing_date", "<=", today),
        ])
        return subs._bill_due()

    def action_run_billing(self):
        subs = self.filtered(lambda s: s.state == "active")
        if not subs:
            raise UserError("Select at least one active subscription.")
        created = subs._bill_due()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Billing",
                "message": "%s invoice(s) created." % len(created),
                "type": "success",
                "sticky": False,
            },
        }
