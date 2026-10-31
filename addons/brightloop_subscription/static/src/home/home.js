/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const ROOT_XMLID = "brightloop_subscription.menu_brightloop_root";

const STEPS = [
    { title: "Create a plan", text: "A plan sets the price and how often a customer is billed.", menu: "brightloop_subscription.menu_brightloop_plans", button: "Open Plans" },
    { title: "Create a subscription", text: "Choose the customer and the plan, then add products and prices.", menu: "brightloop_subscription.menu_brightloop_subscriptions", button: "Open Subscriptions" },
    { title: "Send, confirm and start", text: "Click Send Quotation, then Confirm Order, then Start Subscription.", menu: null },
    { title: "Create the first invoice", text: "Click Create Invoice Now. Invoices are also created automatically every day.", menu: null },
    { title: "Follow payments", text: "Invoices and Reports show what is paid, what is owed and what is overdue.", menu: "brightloop_subscription.menu_brightloop_invoices", button: "Open Invoices" },
];

export class BrightloopHome extends Component {
    static template = "brightloop_subscription.Home";
    static props = ["*"];

    setup() {
        this.menus = useService("menu");
        this.state = useState({ items: [], steps: [] });
        onWillStart(() => this.load());
    }

    load() {
        const root = this.menus.getApps().find((app) => app.xmlid === ROOT_XMLID);
        const items = [];
        const byXmlid = {};
        if (root) {
            const tree = this.menus.getMenuAsTree(root.id);
            for (const child of tree.childrenTree || []) {
                items.push({ id: child.id, name: child.name, actionID: child.actionID, sub: false, menu: child });
                byXmlid[child.xmlid] = child;
                for (const grand of child.childrenTree || []) {
                    items.push({ id: grand.id, name: grand.name, actionID: grand.actionID, sub: true, menu: grand });
                    byXmlid[grand.xmlid] = grand;
                }
            }
        }
        this.state.items = items;
        this.state.steps = STEPS.map((step, i) => {
            const target = (step.menu && byXmlid[step.menu]) || null;
            return { ...step, index: i + 1, target };
        });
    }

    open(menu) {
        if (menu && menu.actionID) {
            this.menus.selectMenu(menu);
        }
    }
}

registry.category("actions").add("brightloop_home", BrightloopHome);