# -*- coding: utf-8 -*-
{
    "name"     : "Module Odoo 15 pour CLAIR-SARL",
    "version"  : "0.1",
    "author"   : "InfoSaône",
    "category" : "InfoSaône",
    "description": """
Module Odoo 15 pour CLAIR-SARL
===================================================
""",
    "maintainer" : "InfoSaône",
    "website"    : "http://www.infosaone.com",
    "depends"    : [
        "base",
        "sale_management",
        "purchase",
        "account",
        "l10n_fr",
        "l10n_fr_fec",
    ],
    "data" : [
        "security/ir.model.access.csv",
        "views/is_affaire_view.xml",
        "views/is_import_clair_views.xml",
        "views/is_modele_commande_view.xml",
        "views/is_preparation_facture_view.xml",
        "views/partner_view.xml",
        "views/product_view.xml",
        "views/purchase_view.xml",
        "views/sale_view.xml",
        "views/account_move_view.xml",
        "views/account_payment_view.xml",
        "views/is_export_compta_views.xml",
        "views/is_courrier_expedie_view.xml",
        "views/is_purchase_order_line.xml",
        "views/res_company_view.xml",
        "views/report_invoice.xml",
        "views/menu.xml",
        "report/purchase_quotation_templates.xml",
        "report/purchase_order_templates.xml",
        "report/sale_report_templates.xml",
        "report/report_templates.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'is_clair_sarl/static/src/scss/styles.scss',
        ],
        'web.assets_qweb': [
            'is_clair_sarl/static/src/xml/**/*',
        ],
       'web.report_assets_common': [
            'is_clair_sarl/static/src/scss/report.scss',
        ]
    },







    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
