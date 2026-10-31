from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBrightloopStage7(TransactionCase):

    def test_password_rule_accepts_strong(self):
        self.env["res.users"]._check_password_policy(["Abcdefg1!"])

    def test_password_rule_rejects_weak(self):
        for pwd in ("Ab1!", "abcdefgh1!", "ABCDEFGH1!", "Abcdefgh12"):
            with self.assertRaises(UserError, msg=pwd):
                self.env["res.users"]._check_password_policy([pwd])

    def test_template_sets_quote_validity(self):
        tpl = self.env["brightloop.quotation.template"].create({"name": "Validity Template"})
        self.assertEqual(tpl.validity_days, 30)
        tpl.validity_days = 10
        sub = self.env["brightloop.subscription"].new({"template_id": tpl.id})
        sub._onchange_template_id()
        self.assertEqual(
            sub.quote_valid_until, fields.Date.context_today(sub) + relativedelta(days=10))

    def test_invoice_dated_at_period_start(self):
        partner = self.env["res.partner"].create({"name": "Date Customer"})
        product = self.env["product.product"].create({"name": "Date Product", "lst_price": 100.0})
        plan = self.env["brightloop.plan"].create({
            "name": "Date Plan", "price": 100.0, "interval": "monthly"})
        sub = self.env["brightloop.subscription"].create({
            "customer_id": partner.id,
            "plan_id": plan.id,
            "start_date": fields.Date.today() - relativedelta(months=2),
            "line_ids": [(0, 0, {
                "product_id": product.id, "quantity": 1.0, "unit_price": 100.0})],
        })
        sub.action_quote()
        sub.action_confirm()
        sub.action_activate()
        invoices = self.env["account.move"].browse(sub._bill_due())
        self.assertGreaterEqual(len(invoices), 2)
        for inv in invoices:
            self.assertEqual(inv.invoice_date, inv.period_start)

    def test_indexes_exist(self):
        self.env.cr.execute(
            "SELECT 1 FROM pg_indexes WHERE indexname = %s",
            ["brightloop_subscription_customer_idx"])
        self.assertTrue(self.env.cr.fetchone())