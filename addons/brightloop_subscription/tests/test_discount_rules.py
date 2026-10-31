from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBrightloopDiscountRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["brightloop.discount.rule"].search([]).write({"active": False})
        cls.partner = cls.env["res.partner"].create({"name": "Rule Customer"})
        cls.product = cls.env["product.product"].create({"name": "Rule Product", "lst_price": 100.0})
        cls.other = cls.env["product.product"].create({"name": "Other Product", "lst_price": 50.0})
        cls.plan = cls.env["brightloop.plan"].create({
            "name": "Rule Plan", "price": 100.0, "interval": "monthly"})

    def _sub(self, start=None):
        vals = {
            "customer_id": self.partner.id,
            "plan_id": self.plan.id,
            "line_ids": [(0, 0, {
                "product_id": self.product.id, "quantity": 1.0, "unit_price": 100.0})],
        }
        if start:
            vals["start_date"] = start
        sub = self.env["brightloop.subscription"].create(vals)
        sub.action_quote()
        sub.action_confirm()
        sub.action_activate()
        return sub

    def _rule(self, **kw):
        vals = {"name": "Test Rule", "discount_type": "percent", "value": 10.0,
                "apply_on": "subscription"}
        vals.update(kw)
        return self.env["brightloop.discount.rule"].create(vals)

    def _first_invoice(self, sub):
        ids = sub._bill_due()
        self.assertTrue(ids)
        return self.env["account.move"].browse(ids[0])

    def test_percent_rule(self):
        rule = self._rule()
        inv = self._first_invoice(self._sub())
        self.assertAlmostEqual(inv.amount_untaxed, 90.0)
        self.assertEqual(rule.usage_count, 1)

    def test_fixed_rule(self):
        self._rule(discount_type="fixed", value=15.0)
        inv = self._first_invoice(self._sub())
        self.assertAlmostEqual(inv.amount_untaxed, 85.0)

    def test_product_rule_other_product(self):
        rule = self._rule(apply_on="product", product_ids=[(6, 0, self.other.ids)])
        inv = self._first_invoice(self._sub())
        self.assertAlmostEqual(inv.amount_untaxed, 100.0)
        self.assertEqual(rule.usage_count, 0)

    def test_minimum_quantity_not_met(self):
        self._rule(min_quantity=5.0)
        inv = self._first_invoice(self._sub())
        self.assertAlmostEqual(inv.amount_untaxed, 100.0)

    def test_expired_rule_ignored(self):
        yesterday = fields.Date.today() - relativedelta(days=1)
        self._rule(date_end=yesterday)
        inv = self._first_invoice(self._sub())
        self.assertAlmostEqual(inv.amount_untaxed, 100.0)

    def test_usage_limit_stops_rule(self):
        rule = self._rule(usage_limit=1)
        sub = self._sub(start=fields.Date.today() - relativedelta(months=2))
        ids = sub._bill_due()
        invoices = self.env["account.move"].browse(ids).sorted("period_start")
        self.assertGreaterEqual(len(invoices), 2)
        self.assertAlmostEqual(invoices[0].amount_untaxed, 90.0)
        self.assertAlmostEqual(invoices[-1].amount_untaxed, 100.0)
        self.assertEqual(rule.usage_count, 1)