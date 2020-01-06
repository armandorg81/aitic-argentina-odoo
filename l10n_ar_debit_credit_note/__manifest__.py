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
    'name': 'Credit and Debit Notes AITIC',
    'version': '2.4',
    'author': "AITIC",
    'maintainer': 'AITIC',
    'website': 'http://www.aitic.com.ar',
    'category': 'Account',
    'summary': 'Invoice refund...',
    'depends': ['base','account','sale_management','purchase'],
    'description': """
Contabilidad: Nota de Débito y Crédito
=============================================================================
1-. Adiciona menú para clasificar los documentos.\n
2-. Adiciona las Notas de Crédito y Débito.\n

AITIC - Asesoría Integral en IT
=====================================================
        """,
    'data': [
        'wizards/account_invoice_refund_view.xml',
        'wizards/account_invoice_debit_view.xml',
        'views/account_invoice_view.xml',
        'views/partner_view.xml',
        'views/account_view.xml',
    ],
    'installable': True,
}
