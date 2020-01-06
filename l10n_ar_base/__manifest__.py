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
    'name': 'Base Argentina location AITIC',
    'version': '2.8',
    'author': "AITIC",
    'maintainer': 'AITIC',
    'website': 'http://www.aitic.com.ar',
    'license': 'AGPL-3',
    'category': 'Localization/Arqentina',
    'summary': 'Localización Argentina.',
    'depends': [
                'base_vat',
                'account_accountant',
                'l10n_ar',
                'l10n_ar_debit_credit_note',
                ],
    'description': """
Localización Argentina por AITIC
=====================================================
1-. Adiciona C.U.I.T. y su validación\n
2-. Adiciona Puntos de Ventas.\n
3-. Adiciona Tipos de comprobantes.\n
4-. Tipos de documentos.\n
5-. Condiciones de Ventas.\n

AITIC - Asesoría Integral en IT
=====================================================

""",
    'data': [
            'security/ir.model.access.csv',
            'security/security.xml',
            'views/base.xml',
            'views/account_view.xml',
            'views/res_partner.xml',
            'views/sale_order_view.xml',
            'views/res_company.xml',
            'views/point_sales_view.xml',
            'views/tipo_comprobante_view.xml',
            'views/account_journal_view.xml',
            'views/tipo_documento_view.xml',
            'views/condicion_venta_view.xml',
            'views/account_tax_view.xml',
            'views/account_invoice_view.xml',
            'views/unidades_medida_view.xml',
            'views/account_payment_view.xml',
            'views/account_move_view.xml',
            'data/account_tax_data.xml',
            'data/tipo_comprobante_data.xml',
            'data/account_journal_data.xml',
            'data/tipo_documento_data.xml',
            'data/condicion_venta_data.xml',
            'views/res_country_view.xml',
            'data/res_country_data.xml',
            'data/ir_config_parameter.xml',
            ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
