from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestBrightloopSubscription(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.product = cls.env["product.product"].create({"name": "Test Product", "lst_price": 100.0})
        cls.plan = cls.env["brightloop.plan"].create({
            "name": "Test Plan", "price": 100.0, "interval": "monthly",
            "allow_pause": True, "allow_early_close": True,
        })
        cls.plan_no_pause = cls.env["brightloop.plan"].create({
            "name": "No Pause Plan", "price": 100.0, "interval": "monthly",
        })

    def _make(self, plan=None, discount=0.0, qty=1.0):
        return self.env["brightloop.subscription"].create({
            "customer_id": self.partner.id,
            "plan_id": (plan or self.plan).id,
            "line_ids": [(0, 0, {
                "product_id": self.product.id, "quantity": qty,
                "unit_price": 100.0, "discount": discount,
            })],
        })

    def _activate(self, sub):
        sub.action_quote()
        sub.action_confirm()
        sub.action_activate()

    def test_number_generated(self):
        self.assertNotEqual(self._make().name, "New")

    def test_confirm_without_lines_fails(self):
        sub = self.env["brightloop.subscription"].create({
            "customer_id": self.partner.id, "plan_id": self.plan.id})
        sub.action_quote()
        with self.assertRaises(UserError):
            sub.action_confirm()

    def test_state_cannot_be_written_directly(self):
        sub = self._make()
        with self.assertRaises(UserError):
            sub.write({"state": "active"})

    def test_lifecycle_and_history(self):
        sub = self._make()
        self._activate(sub)
        self.assertEqual(sub.state, "active")
        self.assertEqual(sub.next_billing_date, sub.start_date)
        sub.action_pause()
        sub.action_resume()
        sub.action_close()
        self.assertEqual(sub.state, "closed")
        self.assertTrue(len(sub.history_ids) >= 6)

    def test_pause_not_allowed(self):
        sub = self._make(plan=self.plan_no_pause)
        self._activate(sub)
        with self.assertRaises(UserError):
            sub.action_pause()

    def test_discount_applied(self):
        sub = self._make(discount=10.0, qty=2.0)
        self.assertAlmostEqual(sub.amount_untaxed, 180.0)

    def test_billing_once_and_duplicate_blocked(self):
        sub = self._make()
        self._activate(sub)
        ids = sub._bill_due()
        self.assertEqual(len(ids), 1)
        self.assertEqual(sub._bill_due(), [])
        inv = self.env["account.move"].browse(ids[0])
        self.assertEqual(inv.state, "posted")
        self.assertEqual(inv.subscription_id, sub)
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"), self.cr.savepoint():
            self.env["account.move"].create({
                "move_type": "out_invoice", "partner_id": self.partner.id,
                "subscription_id": sub.id,
                "period_start": inv.period_start, "period_end": inv.period_end,
            })