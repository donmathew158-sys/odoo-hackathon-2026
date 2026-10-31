from odoo import api, fields, models


class BrightloopQuotationTemplate(models.Model):
    _name = "brightloop.quotation.template"
    _description = "Quotation Template"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    plan_id = fields.Many2one("brightloop.plan", string="Plan")
    duration_months = fields.Integer(string="Duration (months)", help="0 means no expiry date.")
    note = fields.Text()
    line_ids = fields.One2many("brightloop.quotation.template.line", "template_id",
                               string="Lines", copy=True)


class BrightloopQuotationTemplateLine(models.Model):
    _name = "brightloop.quotation.template.line"
    _description = "Quotation Template Line"

    template_id = fields.Many2one("brightloop.quotation.template", required=True,
                                  ondelete="cascade", index=True)
    product_id = fields.Many2one("product.product", required=True)
    quantity = fields.Float(default=1.0)
    unit_price = fields.Float(help="Leave 0 to use the product price.")
    discount = fields.Float(string="Discount (%)")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_price = self.product_id.lst_price