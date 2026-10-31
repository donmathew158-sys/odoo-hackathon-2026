from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

MONTHLY_FACTOR = {"daily": 30.0, "weekly": 52.0 / 12.0, "monthly": 1.0, "yearly": 1.0 / 12.0}


class BrightloopSubscriptionLineExtra(models.Model):
    _inherit = "brightloop.subscription.line"

    discount = fields.Float(string="Discount (%)", default=0.0)

    @api.depends("quantity", "unit_price", "discount", "tax_ids", "currency_id")
    def _compute_amounts(self):
        for line in self:
            price = line.unit_price * (1.0 - (line.discount or 0.0) / 100.0)
            res = line.tax_ids.compute_all(
                price, currency=line.currency_id, quantity=line.quantity,
                product=line.product_id, partner=line.subscription_id.customer_id,
            )
            line.price_subtotal = res["total_excluded"]
            line.price_tax = res["total_included"] - res["total_excluded"]

    @api.constrains("discount")
    def _check_discount(self):
        for line in self:
            if line.discount < 0 or line.discount > 100:
                raise ValidationError("Discount must be between 0 and 100 percent.")


class BrightloopSubscriptionExtra(models.Model):
    _inherit = "brightloop.subscription"

    template_id = fields.Many2one("brightloop.quotation.template", string="Template")
    monthly_recurring = fields.Monetary(
        string="MRR", compute="_compute_monthly_recurring", store=True)
    amount_invoiced = fields.Monetary(compute="_compute_payments")
    amount_paid = fields.Monetary(compute="_compute_payments")
    amount_due = fields.Monetary(compute="_compute_payments")

    @api.depends("amount_untaxed", "plan_id.interval", "state")
    def _compute_monthly_recurring(self):
        for rec in self:
            factor = MONTHLY_FACTOR.get(rec.plan_id.interval, 1.0)
            rec.monthly_recurring = rec.amount_untaxed * factor if rec.state == "active" else 0.0

    def _compute_payments(self):
        Move = self.env["account.move"].sudo()
        for rec in self:
            moves = Move
            if rec.id:
                moves = Move.search([
                    ("subscription_id", "=", rec.id),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                ])
            invoiced = sum(moves.mapped("amount_total"))
            due = sum(moves.mapped("amount_residual"))
            rec.amount_invoiced = invoiced
            rec.amount_due = due
            rec.amount_paid = invoiced - due

    @api.onchange("template_id")
    def _onchange_template_id(self):
        tpl = self.template_id
        if not tpl:
            return
        if tpl.plan_id:
            self.plan_id = tpl.plan_id
        cmds = [(5, 0, 0)]
        for l in tpl.line_ids:
            cmds.append((0, 0, {
                "product_id": l.product_id.id,
                "quantity": l.quantity,
                "unit_price": l.unit_price or l.product_id.lst_price,
                "discount": l.discount,
                "tax_ids": [(6, 0, l.product_id.taxes_id.ids)],
            }))
        self.line_ids = cmds
        if tpl.duration_months and self.start_date:
            self.expiry_date = self.start_date + relativedelta(months=tpl.duration_months)

    def _prepare_invoice_vals(self, start, end):
        vals = super()._prepare_invoice_vals(start, end)
        for cmd, line in zip(vals["invoice_line_ids"], self.line_ids):
            cmd[2]["discount"] = line.discount
        return vals

    def action_run_billing(self):
        today = fields.Date.context_today(self)
        active = self.filtered(lambda s: s.state == "active")
        waiting = active.filtered(lambda s: s.next_billing_date and s.next_billing_date > today)
        res = super().action_run_billing()
        params = res.get("params", {})
        if active and waiting == active and params.get("message", "").startswith("0"):
            params["message"] = "Nothing to bill yet. Next billing date is %s." % min(
                waiting.mapped("next_billing_date"))
            params["type"] = "warning"
        return res