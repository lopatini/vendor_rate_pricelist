# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

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
        для вендорських прайслистів раптом почнуть рахуватись
        неправильно — перше, що перевірити: чи не змінилась логіка
        ОРИГІНАЛЬНОГО _compute_base_price в ядрі нової версії. Це
        типовий ризик full override — треба звіряти при кожному
        апгрейді Odoo, не тільки при встановленні цього модуля."""
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
            vendor_rule = self.pricelist_id.vendor_rate_rule_id
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
