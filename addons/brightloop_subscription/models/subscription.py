from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

STATES = [
    ("draft", "Draft"),
    ("quotation", "Quotation"),
    ("confirmed", "Confirmed"),
    ("active", "Active"),
    ("paused", "Paused"),
    ("closed", "Closed"),
]

TRANSITIONS = {
    "draft": ["quotation", "closed"],
    "quotation": ["confirmed", "closed"],
    "confirmed": ["active", "closed"],
    "active": ["paused", "closed"],
    "paused": ["active", "closed"],
    "closed": [],
}

INTERVAL_DELTA = {
    "daily": {"days": 1},
    "weekly": {"weeks": 1},
    "monthly": {"months": 1},
    "yearly": {"years": 1},
}


class BrightloopSubscription(models.Model):
    _name = "brightloop.subscription"
    _description = "Subscription"
    _inherit = ["mail.thread"]
    _order = "id desc"
    _sql_constraints = [
        ("name_unique", "unique(name)", "Subscription number must be unique."),
    ]

    name = fields.Char(string="Number", readonly=True, copy=False, default="New")
    customer_id = fields.Many2one("res.partner", required=True, tracking=True, index=True)
    plan_id = fields.Many2one("brightloop.plan", required=True, tracking=True, index=True)
    currency_id = fields.Many2one(related="plan_id.currency_id", store=True)
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    expiry_date = fields.Date(tracking=True)
    next_billing_date = fields.Date(readonly=True, copy=False, index=True)
    payment_term_id = fields.Many2one("account.payment.term", string="Payment Terms")
    state = fields.Selection(STATES, default="draft", required=True,
                             readonly=True, copy=False, tracking=True, index=True)
    line_ids = fields.One2many("brightloop.subscription.line", "subscription_id", string="Lines")
    history_ids = fields.One2many("brightloop.subscription.history", "subscription_id", string="History")
    amount_untaxed = fields.Monetary(compute="_compute_amounts", store=True)
    amount_tax = fields.Monetary(compute="_compute_amounts", store=True)
    amount_total = fields.Monetary(compute="_compute_amounts", store=True)

    @api.depends("line_ids.price_subtotal", "line_ids.price_tax")
    def _compute_amounts(self):
        for rec in self:
            untaxed = sum(rec.line_ids.mapped("price_subtotal"))
            tax = sum(rec.line_ids.mapped("price_tax"))
            rec.amount_untaxed = untaxed
            rec.amount_tax = tax
            rec.amount_total = untaxed + tax

    @api.constrains("start_date", "expiry_date")
    def _check_dates(self):
        for rec in self:
            if rec.expiry_date and rec.expiry_date < rec.start_date:
                raise ValidationError("Expiry date cannot be before start date.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("brightloop.subscription") or "New"
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals and not self.env.context.get("bl_state_change"):
            raise UserError("Status can only be changed with the workflow buttons.")
        return super().write(vals)

    def _log(self, old, new, note=False):
        self.env["brightloop.subscription.history"].create({
            "subscription_id": self.id,
            "from_state": old,
            "to_state": new,
            "note": note,
        })

    def _change_state(self, new_state):
        for rec in self:
            if new_state not in TRANSITIONS[rec.state]:
                raise UserError("Invalid status change: %s to %s." % (rec.state, new_state))
            old = rec.state
            rec.with_context(bl_state_change=True).write({"state": new_state})
            rec._log(old, new_state)

    def action_quote(self):
        self._change_state("quotation")

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Add at least one line before confirming.")
            for line in rec.line_ids:
                if line.quantity < rec.plan_id.min_quantity:
                    raise UserError("Minimum quantity for this plan is %s." % rec.plan_id.min_quantity)
        self._change_state("confirmed")

    def action_activate(self):
        for rec in self:
            rec._change_state("active")
            if not rec.next_billing_date:
                rec.next_billing_date = rec.start_date

    def action_pause(self):
        for rec in self:
            if not rec.plan_id.allow_pause:
                raise UserError("This plan does not allow pausing.")
        self._change_state("paused")

    def action_resume(self):
        self._change_state("active")

    def action_close(self):
        today = fields.Date.context_today(self)
        for rec in self:
            early = rec.state in ("active", "paused") and rec.expiry_date and rec.expiry_date > today
            if early and not rec.plan_id.allow_early_close:
                raise UserError("This plan does not allow early closure.")
        self._change_state("closed")

    def action_renew(self):
        for rec in self:
            if rec.state != "active":
                raise UserError("Only active subscriptions can be renewed.")
            if not rec.plan_id.allow_renew:
                raise UserError("This plan does not allow renewal.")
            delta = relativedelta(**INTERVAL_DELTA[rec.plan_id.interval])
            rec.expiry_date = (rec.expiry_date or rec.start_date) + delta
            rec._log(rec.state, rec.state, "Renewed until %s" % rec.expiry_date)


class BrightloopSubscriptionLine(models.Model):
    _name = "brightloop.subscription.line"
    _description = "Subscription Line"

    subscription_id = fields.Many2one("brightloop.subscription", required=True,
                                      ondelete="cascade", index=True)
    currency_id = fields.Many2one(related="subscription_id.currency_id", store=True)
    product_id = fields.Many2one("product.product", required=True)
    quantity = fields.Float(default=1.0, required=True)
    unit_price = fields.Monetary(required=True)
    tax_ids = fields.Many2many("account.tax", domain=[("type_tax_use", "=", "sale")])
    price_subtotal = fields.Monetary(compute="_compute_amounts", store=True)
    price_tax = fields.Monetary(compute="_compute_amounts", store=True)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_price = self.product_id.lst_price
            self.tax_ids = self.product_id.taxes_id

    @api.depends("quantity", "unit_price", "tax_ids", "currency_id")
    def _compute_amounts(self):
        for line in self:
            res = line.tax_ids.compute_all(
                line.unit_price, currency=line.currency_id, quantity=line.quantity,
                product=line.product_id, partner=line.subscription_id.customer_id,
            )
            line.price_subtotal = res["total_excluded"]
            line.price_tax = res["total_included"] - res["total_excluded"]

    @api.constrains("quantity", "unit_price")
    def _check_values(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError("Quantity must be greater than zero.")
            if line.unit_price < 0:
                raise ValidationError("Unit price cannot be negative.")


class BrightloopSubscriptionHistory(models.Model):
    _name = "brightloop.subscription.history"
    _description = "Subscription History"
    _order = "id desc"

    subscription_id = fields.Many2one("brightloop.subscription", required=True,
                                      ondelete="cascade", index=True)
    from_state = fields.Selection(STATES)
    to_state = fields.Selection(STATES)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    date = fields.Datetime(default=fields.Datetime.now)
    note = fields.Char()
