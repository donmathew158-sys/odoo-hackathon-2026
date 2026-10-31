{
    "name": "Brightloop Subscription Management",
    "version": "18.0.1.0.0",
    "summary": "Subscriptions, recurring billing, payments and portal",
    "category": "Sales",
    "author": "Team Brightloop",
    "license": "LGPL-3",
    "depends": ["base", "mail", "product", "account", "portal"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/plan_views.xml",
    ],
    "application": True,
    "installable": True,
}
