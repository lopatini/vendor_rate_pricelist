{
    "name": "Vendor Rate Pricelist (курс вендора у прайслисті)",
    "summary": "Живий перерахунок цін у прайслисті сайту за комерційним "
    "курсом вендора (Шар 2, vendor_rate_formula) замість стандартного "
    "курсу валют Odoo",
    "version": "19.0.1.1.1",
    "category": "Sales",
    "author": "Ivan Lopatin",
    "license": "LGPL-3",
    # Технічна назва vendor_rate_formula на цьому сервері мала (це не
    # Currency_rate_feed) — тут регістр стандартний, перевіряти не
    # треба. Сам Currency_rate_feed НЕ вказуємо явно — це транзитивна
    # залежність через vendor_rate_formula, Odoo підхопить сам.
    "depends": ["product", "vendor_rate_formula"],
    "data": [
        "views/product_pricelist_item_views.xml",
    ],
    "installable": True,
    "application": False,
}
