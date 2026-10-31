from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


def _ensure_indexes(cr, table, specs):
    """Create an index only when every column exists, so an upgrade never fails here."""
    cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", [table])
    columns = {row[0] for row in cr.fetchall()}
    for name, cols in specs:
        if all(col in columns for col in cols):
            cr.execute("CREATE INDEX IF NOT EXISTS %s ON %s (%s)" % (name, table, ", ".join(cols)))


class ResUsersPasswordRule(models.Model):
    _inherit = "res.users"

    @api.model
    def _check_password_policy(self, passwords):
        result = super()._check_password_policy(passwords)
        for password in passwords:
            if not password:
                continue
            missing = []
            if len(password) <= 8:
                missing.append("be longer than 8 characters")
            if not any(ch.isupper() for ch in password):
                missing.append("contain an uppercase letter")
            if not any(ch.islower() for ch in password):
                missing.append("contain a lowercase letter")
            if not any((not ch.isalnum()) and (not ch.isspace()) for ch in password):
                missing.append("contain a special character (for example ! @ # $)")
            if missing:
                raise UserError("The password must " + ", ".join(missing) + ".")
        return result


class BrightloopTemplateValidity(models.Model):
    _inherit = "brightloop.quotation.template"

    validity_days = fields.Integer(
        string="Quote valid for (days)", default=30,
        help="How many days a quotation made from this template stays valid.")


class BrightloopSubscriptionStage7(models.Model):
    _inherit = "brightloop.subscription"

    quote_valid_until = fields.Date(string="Quote valid until")

    def init(self):
        super().init()
        _ensure_indexes(self._cr, self._table, [
            ("brightloop_subscription_state_billing_idx", ("state", "next_billing_date")),
            ("brightloop_subscription_customer_idx", ("customer_id",)),
        ])

    @api.onchange("template_id")
    def _onchange_template_id(self):
        super()._onchange_template_id()
        tpl = self.template_id
        if tpl and tpl.validity_days:
            self.quote_valid_until = fields.Date.context_today(self) + relativedelta(days=tpl.validity_days)

    def _prepare_invoice_vals(self, start, end):
        vals = super()._prepare_invoice_vals(start, end)
        vals["invoice_date"] = start
        return vals