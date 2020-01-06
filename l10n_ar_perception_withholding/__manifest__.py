# -*- coding: utf-8 -*-
{
    'name': "Percepciones y Retenciones IIBB ARBA",

    'summary': """Percepciones y Retenciones""",

    'description': """
        Percepciones y Retenciones
    """,

    'author': "AITIC",
    'website': "http://www.aitic.com.ar",

    'category': 'Localization/Argentina',
    'version': '1.0',

    'depends': ['purchase', 'l10n_ar_account_group_withholding', 'l10n_ar_report'],

    'data': [
        'security/ir.model.access.csv',
        'data/account_data.xml',
        'data/arba_activity_data.xml',
        'views/res_arba_config_view.xml',
        'views/res_company.xml',
        'views/res_partner.xml',
        'views/account_tax_view.xml',
        'views/account_invoice_view.xml',
        'views/account_payment_group_view.xml',
        'views/account_withholding_view.xml',
        'report/report_invoice.xml',
        'report/report_aliquot_withholding.xml',
        'report/aliquot_withholding_report.xml',
        'wizards/arba_data_wizard_view.xml',
        'wizards/account_aliquot_arba_wizard_view.xml',
    ],
}
