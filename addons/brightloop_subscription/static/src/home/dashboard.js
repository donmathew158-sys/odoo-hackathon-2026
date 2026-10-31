/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const POSTED = [["subscription_id", "!=", false], ["move_type", "=", "out_invoice"], ["state", "=", "posted"]];
const UNPAID = [["payment_state", "in", ["not_paid", "partial"]]];
const MODULE = "brightloop_subscription.";

function todayIso() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function money(value, code) {
    try {
        return new Intl.NumberFormat(undefined, { style: "currency", currency: code }).format(value);
    } catch {
        return `${code} ${value.toFixed(2)}`;
    }
}

export class BrightloopDashboard extends Component {
    static template = "brightloop_subscription.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.company = useService("company");
        this.state = useState({ cards: [], loading: true });
        onWillStart(() => this.load());
    }

    definitions(today) {
        return [
            { key: "active", title: "Active subscriptions", kind: "count", model: "brightloop.subscription",
              domain: [["state", "=", "active"]], action: "action_brightloop_active_subs", hint: "Currently billing" },
            { key: "mrr", title: "Monthly recurring revenue", kind: "sum", model: "brightloop.subscription",
              domain: [["state", "=", "active"]], field: "monthly_recurring", group: "currency_id",
              action: "action_brightloop_mrr", hint: "Active subscriptions, before tax" },
            { key: "billed", title: "Billed revenue", kind: "sum", model: "account.move", domain: POSTED,
              field: "amount_total_signed", action: "action_brightloop_revenue", hint: "All posted subscription invoices, tax included" },
            { key: "owed", title: "Amount outstanding", kind: "sum", model: "account.move", domain: [...POSTED, ...UNPAID],
              field: "amount_residual_signed", action: "action_brightloop_outstanding", hint: "Unpaid or part-paid invoices" },
            { key: "overdueInv", title: "Overdue invoices", kind: "count", model: "account.move",
              domain: [...POSTED, ...UNPAID, ["invoice_date_due", "<", today]],
              action: "action_brightloop_overdue_invoices", hint: "Past their due date", tone: "danger" },
            { key: "overdueSubs", title: "Overdue subscriptions", kind: "count", model: "brightloop.subscription",
              domain: [["is_overdue", "=", true]], action: "action_brightloop_overdue",
              hint: "Customers with an unpaid invoice past due", tone: "danger" },
        ];
    }

    async companyCurrency() {
        try {
            const rows = await this.orm.read("res.company", [this.company.currentCompany.id], ["currency_id"]);
            return rows[0].currency_id[1];
        } catch {
            return null;
        }
    }

    async compute(def, companyCode) {
        const card = { key: def.key, title: def.title, hint: def.hint, action: def.action, tone: def.tone || "", lines: [], error: false };
        try {
            if (def.kind === "count") {
                card.lines = [String(await this.orm.searchCount(def.model, def.domain))];
            } else if (def.group) {
                const groups = await this.orm.readGroup(def.model, def.domain, [`${def.field}:sum`], [def.group], { lazy: false });
                card.lines = groups.map((g) => money(g[def.field] ?? g[`${def.field}:sum`] ?? 0, g[def.group][1]));
                if (!card.lines.length && companyCode) {
                    card.lines = [money(0, companyCode)];
                }
            } else {
                const groups = await this.orm.readGroup(def.model, def.domain, [`${def.field}:sum`], [], { lazy: false });
                const total = groups.length ? (groups[0][def.field] ?? groups[0][`${def.field}:sum`] ?? 0) : 0;
                card.lines = [companyCode ? money(total, companyCode) : total.toFixed(2)];
            }
        } catch {
            card.error = true;
            card.lines = ["-"];
        }
        return card;
    }

    async load() {
        this.state.loading = true;
        const code = await this.companyCurrency();
        this.state.cards = await Promise.all(this.definitions(todayIso()).map((d) => this.compute(d, code)));
        this.state.loading = false;
    }

    open(card) {
        this.action.doAction(MODULE + card.action);
    }
}

registry.category("actions").add("brightloop_dashboard", BrightloopDashboard);