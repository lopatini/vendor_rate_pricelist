# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    vendor_rate_rule_id = fields.Many2one(
        "vendor.rate.rule", string="Курс вендора",
        help="Якщо вказано — конвертація валюти для товарів цього "
        "прайслиста (коли ціна береться з ІНШОГО прайслиста в іншій "
        "валюті, тобто у правилі compute_price='formula'/'percentage' "
        "з base='pricelist') рахується НЕ стандартним курсом ядра Odoo "
        "(res.currency.rate), а живим комерційним курсом цього "
        "вендора з Шару 2 (vendor.rate.rule.get_commercial_rate()) — "
        "тобто враховує базове джерело (НБУ/Приват) і надбавку з "
        "vendor_rate_formula, а не офіційний курс з ядра.\n\n"
        "УВАГА: на 'фіксовані' ціни (compute_price='fixed') це поле "
        "НЕ впливає — Odoo взагалі ніколи не конвертує валюту для "
        "fixed-цін, це поведінка ядра (перевірено на реальному коді "
        "product/models/product_pricelist_item.py, гілка 19.0), не "
        "наша обмеженість. Використовувати цей прайслист ЯК ЗОВНІШНІЙ "
        "(куди приходять клієнти) поверх окремого 'сирого' прайслиста "
        "вендора в його валюті (base_pricelist_id на правилі), інакше "
        "поле ні на що не впливає.",
    )
