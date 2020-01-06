# -*- coding: utf-8 -*-
{
    'name': "Percepciones y Retenciones IVA AITIC",

    'summary': """Percepciones y Retenciones IVA""",

    'description': """
        Percepciones y Retenciones
    """,

    'author': "AITIC",
    'website': "http://www.aitic.com.ar",

    'category': 'Localization/Argentina',
    'version': '0.1',

    'depends': ['l10n_ar_perception_withholding_agip'],

    'data': [
             'data/account_data.xml',
             # 'data/article_section_data.xml',
             'views/account_invoice_view.xml',
             'views/res_company.xml',
             'views/res_partner.xml',
             'views/account_withholding_view.xml',
             'views/account_payment_group_view.xml',
             'report/report_aliquot_withholding.xml',
             'report/aliquot_withholding_report.xml',
             'wizards/account_aliquot_wizard_view.xml',
             ],
}
