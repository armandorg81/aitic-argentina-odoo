# -*- coding: utf-8 -*-
{
    'name': "Percepciones y Retenciones IIBB AGIP",

    'summary': """Percepciones y Retenciones Capital Federal Argentina""",

    'description': """
        Percepciones y Retenciones Capital Federal Argentina
    """,

    'author': "AITIC",
    'website': "http://www.aitic.com.ar",

    'category': 'Localization/Argentina',
    'version': '1.0',

    'depends': ['l10n_ar_perception_withholding', 'queue_job'],

    'data': [
        'security/ir.model.access.csv',
        'data/account_data.xml',
        'views/res_company.xml',
        'views/perception_withholding_agip.xml',
        'views/res_partner.xml',
        # 'views/account_tax_view.xml',
        'views/account_invoice_view.xml',
        'views/account_payment_group_view.xml',
        'views/account_withholding_view.xml',
        # 'wizards/agip_data_wizard_view.xml',
        'wizards/account_aliquot_agip_wizard_view.xml',
        'report/report_aliquot_withholding.xml',
        'report/report_invoice.xml'
    ],
}