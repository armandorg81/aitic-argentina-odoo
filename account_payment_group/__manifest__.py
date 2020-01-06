# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2017 AITIC
#    (<http://www.falconsolutions.cl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Pagos Múltiples AITIC',
    'version': '2.0',
    'author': "AITIC",
    'maintainer': 'AITIC',
    'website': 'http://www.aitic.com.ar',
    'license': 'LGPL-3',
    'category': 'Account',
    'summary': 'Localización Argentina.',
    'depends': [
                "base",
                "account_accountant",
                "account_cancel",
                "l10n_ar_account_check",
                "l10n_ar_base",
                "account_reports"
                ],
    'description': """
Payment with Several Methods by AITIC
=====================================================
1-. Pago \n
2-. Cheques.\n
3-. Transferencia.\n

AITIC - Asesoría Integral en IT
=====================================================

""",
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizards/account_payment_group_invoice_wizard_view.xml',
        'wizards/res_config_view.xml',
        'data/account_payment_data.xml',
        'views/account_payment_view.xml',
        'views/account_move_line_view.xml',
        'views/account_payment_group_view.xml',
        'views/account_invoice_view.xml',
        'views/res_company_view.xml',
        'views/account_journal_dashboard_view.xml',
        'views/account_payment_widget.xml',
        'report/report_group_payment.xml',
        'report/account_payment_group_report.xml'],
    'qweb': [
        "static/src/xml/account_payment.xml",
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
