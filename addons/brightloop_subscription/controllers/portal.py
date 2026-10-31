from urllib.parse import quote

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

ACTIONS = {"pause": "action_pause", "resume": "action_resume", "close": "action_close"}


class BrightloopPortal(CustomerPortal):

    def _bl_domain(self):
        partner = request.env.user.partner_id.commercial_partner_id
        return [("customer_id", "child_of", partner.id), ("state", "!=", "draft")]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "subscription_count" in counters:
            values["subscription_count"] = request.env["brightloop.subscription"].sudo().search_count(
                self._bl_domain())
        return values

    @http.route("/my/subscriptions", type="http", auth="user", website=True)
    def portal_my_subscriptions(self, **kw):
        subs = request.env["brightloop.subscription"].sudo().search(self._bl_domain())
        return request.render("brightloop_subscription.portal_my_subscriptions",
                              {"subscriptions": subs, "page_name": "subscriptions"})

    @http.route("/my/subscriptions/<int:sub_id>", type="http", auth="user", website=True)
    def portal_subscription_detail(self, sub_id, error=None, **kw):
        sub = request.env["brightloop.subscription"].sudo().search(
            self._bl_domain() + [("id", "=", sub_id)], limit=1)
        if not sub:
            return request.redirect("/my")
        invoices = request.env["account.move"].sudo().search([
            ("subscription_id", "=", sub.id), ("state", "=", "posted")])
        return request.render("brightloop_subscription.portal_subscription_detail", {
            "sub": sub, "invoices": invoices, "error": error, "page_name": "subscription"})

    @http.route("/my/subscriptions/<int:sub_id>/action/<string:action>", type="http",
                auth="user", methods=["POST"], website=True)
    def portal_subscription_action(self, sub_id, action, **kw):
        sub = request.env["brightloop.subscription"].sudo().search(
            self._bl_domain() + [("id", "=", sub_id)], limit=1)
        if not sub or action not in ACTIONS:
            return request.redirect("/my")
        try:
            getattr(sub, ACTIONS[action])()
        except UserError as e:
            return request.redirect("/my/subscriptions/%s?error=%s" % (sub_id, quote(str(e.args[0]))))
        return request.redirect("/my/subscriptions/%s" % sub_id)