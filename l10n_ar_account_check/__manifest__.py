# -*- coding: utf-8 -*-
{
    'name': 'Gestión de cheques contables',
    'version': '12.5',
    'category': 'Accounting',
    'summary': 'Gestión de cheques contables, tanto de cheques propios como de terceros.',
    'author': 'AITIC',
    'website': "http://www.aitic.com.ar",
    'category': 'Localization/Argentina',
    'images': [
    ],
    'depends': [
        'account_cancel',
        'account_payment_fix',
        'l10n_ar_base',
    ],
    'data': [
        'data/account_payment_method_data.xml',
        'data/account_data.xml',
        'wizard/account_check_action_wizard_view.xml',
        'views/account_payment_view.xml',
        'views/account_check_view.xml',
        'views/account_journal_dashboard_view.xml',
        'views/account_journal_view.xml',
        'views/account_checkbook_view.xml',
        'views/res_company_view.xml',
        'views/account_chart_template_view.xml',
        'security/ir.model.access.csv',
        'security/account_check_security.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
