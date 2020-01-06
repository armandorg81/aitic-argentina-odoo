# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2019 AITIC
#
##############################################################################

{
    'name': 'Argentina Reports AITIC',
    'version': '10.0.0.1.0',
    'author': "AITIC",
    'maintainer': 'AITIC',
    'website': 'http://www.aitic.com.ar',
    'license': 'AGPL-3',
    'category': 'Localization/Arqentina',
    'summary': 'Localización Argentina.',
    'depends': [
                'l10n_ar_account_group_withholding',
                ],
    'description': """
Reportes y formatos para localización Argentina
=====================================================
1-. Formato personalizado de facturas\n

AITIC - Asesoría Integral en IT
=====================================================
""",
    'data': [
        'views/account_invoice_view.xml',
        'views/account_payment_view.xml',
        'wizards/account_cxc_chq_wizard_view.xml',
        'views/res_company_view.xml',
        'report/report_invoice.xml',
        'report/report_payment.xml',
        'report/report_payment_receipt.xml',
        'report/sale_report_templates.xml',
        'report/account_cxc_chq_report_view.xml',
        'report/account_cxp_chq_report_view.xml',
        'report/account_report.xml',
        'data/email_template.xml',
        'data/report_invoice_data.xml'
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
