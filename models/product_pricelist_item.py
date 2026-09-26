# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    # УВАГА: поле навмисно на ПРАВИЛІ (item), а не на прайслисті
    # (product.pricelist) — так було в першій версії модуля, і це
    # виявилось архітектурною помилкою. На реальному сайті для всіх
    # відвідувачів активний ОДИН прайслист одразу (Odoo вибирає його
    # для всієї сесії/кошика, не окремо для кожного товару), тому
    # правила РІЗНИХ вендорів (Adobe, Microsoft, ...) фізично мусять
    # жити в одному й тому самому "живому" сайтовому прайслисті —
    # просто кожне правило застосовується на свою категорію/товар
    # (applied_on). Якщо тримати курс вендора на рівні прайслиста
    # цілком, підтримати другого вендора в тому самому прайслисті
    # вже неможливо. На рівні правила — можливо: кожне правило під
    # свій vendor.rate.rule.
    vendor_rate_rule_id = fields.Many2one(
        "vendor.rate.rule", string="Курс вендора",
        help="Якщо вказано — конвертація валюти ДЛЯ ЦЬОГО ПРАВИЛА "
        "(коли ціна береться з ІНШОГО прайслиста в іншій валюті, тобто "
        "'На основі' = 'Прайслист' / base='pricelist', незалежно від "
        "того, чи компute_price = 'percentage' чи 'formula') рахується "
        "НЕ стандартним курсом ядра Odoo (res.currency.rate), а живим "
        "комерційним курсом цього вендора з Шару 2 "
        "(vendor.rate.rule.get_commercial_rate()) — тобто враховує "
        "базове джерело (НБУ/Приват) і надбавку з vendor_rate_formula, "
        "а не офіційний курс з ядра.\n\n"
        "УВАГА: на 'фіксовані' ціни (compute_price='fixed') це поле НЕ "
        "впливає — Odoo взагалі ніколи не конвертує валюту для "
        "fixed-цін, це поведінка ядра. Заповнювати ТІЛЬКИ на правилі, "
        "яке посилається на інший (сирий, у валюті вендора) прайслист "
        "через поле 'Інший прайслист' (base_pricelist_id) — інакше "
        "поле ні на що не впливає. Правило потрібно тримати у тому "
        "прайслисті, який реально активний на сайті для клієнтів "
        "(перевірити: Продажі → Налаштування → Прайс-листи, поле "
        "'Можна вибрати'/групи країн/чи це прайслист 'За "
        "замовчуванням') — а не в окремому \"сайтовому\" прайслисті "
        "на кожного вендора, бо для одного відвідувача сайту в один "
        "момент активний лише ОДИН прайслист на весь каталог.",
    )

    def _compute_base_price(self, product, quantity, uom, date, currency, **kwargs):
        """ПОВНЕ перевизначення (не super() + патч) — бо стандартна
        конвертація валюти в ядрі відбувається ВСЕРЕДИНІ цього самого
        методу, одним рядком в кінці, і немає способу підмінити лише
        той рядок без повторення решти логіки. Код нижче — 1:1 копія
        product.pricelist.item._compute_base_price() з
        addons/product/models/product_pricelist_item.py (гілка 19.0,
        звірено напряму з реальним джерелом перед написанням), ЗІ
        ЗМІНЕНОЮ лише самою конвертацією валюти (див. коментар нижче).

        ⚠️ Якщо після оновлення Odoo (мінорний/мажорний апгрейд) ціни
        для вендорських правил раптом почнуть рахуватись неправильно —
        перше, що перевірити: чи не змінилась логіка ОРИГІНАЛЬНОГО
        _compute_base_price в ядрі нової версії. Це типовий ризик full
        override — треба звіряти при кожному апгрейді Odoo, не тільки
        при встановленні цього модуля.

        v1.1.0: раніше курс вендора читався з self.pricelist_id (усього
        прайслиста), тепер — з self (конкретного правила/item). Див.
        коментар при полі vendor_rate_rule_id вище — причина в тому,
        що на сайті для одного відвідувача активний ОДИН прайслист на
        ВСІ товари одразу, і правила різних вендорів мусять жити в
        ньому поруч, кожне зі своїм курсом."""
        currency.ensure_one()

        rule_base = self.base or "list_price"
        if rule_base == "pricelist" and self.base_pricelist_id:
            price = self.base_pricelist_id._get_product_price(
                product, quantity, currency=self.base_pricelist_id.currency_id,
                uom=uom, date=date, **kwargs
            )
            src_currency = self.base_pricelist_id.currency_id
        elif rule_base == "standard_price":
            src_currency = product.cost_currency_id
            price = product._price_compute(rule_base, uom=uom, date=date)[product.id]
        else:  # list_price
            src_currency = product.currency_id
            price = product._price_compute(rule_base, uom=uom, date=date)[product.id]

        if src_currency != currency:
            # sudo() навмисно: ця гілка рахує ціну для БУДЬ-ЯКОГО
            # відвідувача сайту, включно з незалогіненим (публічним)
            # користувачем, а vendor.rate.rule навмисно закрита моделлю
            # (лише base.group_system). get_commercial_rate() нижче й
            # сам захищає себе sudo(), але sudo() тут теж — щоб навіть
            # сама перевірка "чи взагалі вказано правило" (обхід полів
            # vendor.rate.rule при `if vendor_rule:`) не залежала від
            # прав користувача, що ініціював розрахунок (виявлено
            # користувачем 2026-09-26, див. claude/currency_rate_feed.md).
            vendor_rule = self.vendor_rate_rule_id.sudo()
            if vendor_rule:
                # Живий комерційний курс вендора (Шар 2) замість
                # стандартного res.currency.rate (курс НБУ з ядра).
                on_date = fields.Date.to_date(date) if date else None
                rate = vendor_rule.get_commercial_rate(on_date)
                if not rate:
                    # Немає чинного курсу (Шар 1/2) на цю дату —
                    # свідомо НЕ фолбечимо на стандартний курс ядра
                    # (це дало б непомітно іншу ціну без жодного
                    # попередження). Явний 0 — помітно на сайті/в
                    # звітах, легше знайти причину.
                    return 0.0
                price = price * rate
            else:
                price = src_currency._convert(
                    price, currency, self.env.company, date, round=False
                )

        return price
