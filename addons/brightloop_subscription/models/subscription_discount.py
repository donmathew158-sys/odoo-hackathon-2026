from odoo import fields, models


class BrightloopSubscriptionDiscount(models.Model):
    _inherit = "brightloop.subscription"

    def _prepare_invoice_vals(self, start, end):
        vals = super()._prepare_invoice_vals(start, end)
        today = fields.Date.context_today(self)
        Rule = self.env["brightloop.discount.rule"].sudo()
        rules = Rule.search([]).filtered(lambda r: r._is_available(today))
        lines = self.line_ids
        factor = {line.id: 1.0 for line in lines}
        used = Rule
        for rule in rules:
            if rule.apply_on == "subscription":
                matched = lines
            else:
                matched = lines.filtered(lambda l: l.product_id in rule.product_ids)
            if not matched:
                continue
            base = sum(matched.mapped("price_subtotal"))
            qty = sum(matched.mapped("quantity"))
            if base <= 0 or base < rule.min_amount or qty < rule.min_quantity:
                continue
            if rule.discount_type == "percent":
                pct = rule.value
            else:
                pct = rule.value / base * 100.0
            pct = min(max(pct, 0.0), 100.0)
            for line in matched:
                factor[line.id] *= 1.0 - pct / 100.0
            used |= rule
        if used:
            for cmd, line in zip(vals["invoice_line_ids"], lines):
                keep = (1.0 - (line.discount or 0.0) / 100.0) * factor[line.id]
                cmd[2]["discount"] = 100.0 * (1.0 - keep)
            for rule in used:
                rule.usage_count += 1
        return vals