from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BrightloopDiscountRule(models.Model):
    _name = "brightloop.discount.rule"
    _description = "Discount Rule"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    discount_type = fields.Selection(
        [("percent", "Percentage"), ("fixed", "Fixed amount")],
        required=True, default="percent")
    value = fields.Float(required=True)
    apply_on = fields.Selection(
        [("subscription", "Whole subscription"), ("product", "Specific products")],
        required=True, default="subscription")
    product_ids = fields.Many2many("product.product", string="Products")
    min_amount = fields.Float(string="Minimum purchase")
    min_quantity = fields.Float(string="Minimum quantity")
    date_start = fields.Date(string="Start date")
    date_end = fields.Date(string="End date")
    usage_limit = fields.Integer(help="0 means unlimited.")
    usage_count = fields.Integer(readonly=True, copy=False)
    status = fields.Char(compute="_compute_status")

    @api.depends("active", "date_start", "date_end", "usage_limit", "usage_count")
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for r in self:
            if not r.active:
                s = "Inactive"
            elif r.date_start and today < r.date_start:
                s = "Scheduled"
            elif r.date_end and today > r.date_end:
                s = "Expired"
            elif r.usage_limit and r.usage_count >= r.usage_limit:
                s = "Used up"
            else:
                s = "Running"
            r.status = s

    @api.constrains("value", "discount_type", "date_start", "date_end", "apply_on", "product_ids")
    def _check_rule(self):
        for r in self:
            if r.value <= 0:
                raise ValidationError("The discount value must be greater than 0.")
            if r.discount_type == "percent" and r.value > 100:
                raise ValidationError("A percentage discount cannot exceed 100.")
            if r.date_start and r.date_end and r.date_end < r.date_start:
                raise ValidationError("The end date cannot be before the start date.")
            if r.apply_on == "product" and not r.product_ids:
                raise ValidationError("Choose at least one product for this rule.")

    def _is_available(self, today):
        self.ensure_one()
        if not self.active:
            return False
        if self.date_start and today < self.date_start:
            return False
        if self.date_end and today > self.date_end:
            return False
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        return True