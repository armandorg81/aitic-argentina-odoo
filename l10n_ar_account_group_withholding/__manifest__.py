# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2017 Marlon Falcón Hernandez
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
    'name': 'Retenciones de Ganancias en Pagos Múltiples AITIC',
    'version': '3.3',
    'author': "AITIC",
    'maintainer': 'AITIC',
    'website': 'http://www.aitic.com.ar',
    'license': 'AGPL-3',
    'category': 'Localization/Argentina',
    'summary': 'Localización Argentina.',
    'depends': ['l10n_ar_facturae','account_payment_group'],
    'description': """""",
    'data': [
            'security/ir.model.access.csv',
            'data/account_data.xml',
            'data/sequence_data.xml',
            'data/regimen_retencion_data.xml',
            'data/withholding_certificate_data.xml',
            'views/base.xml',
            'views/account_payment_view.xml',
            'views/account_journal_view.xml',
            'views/afip_views.xml',
            'views/regimen_retencion_view.xml',
            'views/account_withholding_view.xml',
            'views/res_company_view.xml',
            'views/res_partner_view.xml',
            'views/account_payment_group_view.xml',
            'report/withholding_report.xml',
            'report/withholding_report_templates.xml',
            'report/withholding_earnings_report.xml',
            'report/report_group_payment.xml',
            'wizards/account_withholding_wizard_view.xml',
            ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
