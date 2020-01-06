# -*- coding: utf-8 -*-
{
    'name': "Retenciones IIBB Santa Fe",

    'summary': """Retenciones Santa Fe""",

    'description': """
        Retenciones Santa Fé
    """,

    'author': "AITIC",
    'website': "http://www.aitic.com.ar",

    'category': 'Localization/Argentina',
    'version': '1.1',

    'depends': ['purchase', 'l10n_ar_account_group_withholding', 'l10n_ar_report'],

    'data': ['security/ir.model.access.csv',
             'data/account_data.xml',
             'data/article_section_data.xml',
             'views/res_company.xml',
             'views/res_partner.xml',
             'views/article_section_view.xml',
             'views/account_payment_group_view.xml',
             'views/account_withholding_view.xml',
             'views/account_invoice_view.xml',
             'views/account_tax_view.xml',
             'report/report_aliquot_withholding.xml',
             'report/aliquot_withholding_report.xml',
             'wizards/account_aliquot_sf_wizard_view.xml',
             ],
}