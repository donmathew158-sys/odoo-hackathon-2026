from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BrightloopPlan(models.Model):
    _name = "brightloop.plan"
    _description = "Subscription Plan"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    product_id = fields.Many2one("product.product", string="Product")
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    price = fields.Monetary(required=True, currency_field="currency_id")
    interval = fields.Selection(
        [("daily", "Daily"), ("weekly", "Weekly"),
         ("monthly", "Monthly"), ("yearly", "Yearly")],
        required=True, default="monthly",
    )
    min_quantity = fields.Integer(default=1)
    start_date = fields.Date()
    end_date = fields.Date()
    auto_close = fields.Boolean(string="Automatic Closure")
    allow_early_close = fields.Boolean(string="Allow Early Closure")
    allow_pause = fields.Boolean(string="Allow Pause")
    allow_renew = fields.Boolean(string="Allow Renewal", default=True)

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError("End date cannot be before start date.")

    @api.constrains("price", "min_quantity")
    def _check_values(self):
        for rec in self:
            if rec.price < 0:
                raise ValidationError("Price cannot be negative.")
            if rec.min_quantity < 1:
                raise ValidationError("Minimum quantity must be at least 1.")
