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
    'name': 'Factura Electrónica Argentina AITIC',
    'version': '20.0',
    'author': "AITIC",
    'maintainer': 'AITIC',
    'website': 'http://www.aitic.com.ar',
    'license': 'AGPL-3',
    'category': 'Localization/Arqentina',
    'summary': 'Localización Argentina.',
    'depends': [
                'l10n_ar_base',
                ],
    'description': """
Módulo Facturacion Electrónica Argentina
=====================================================
1-. Permite el trabajo con documentos electrónicos. \n

AITIC - Asesoría Integral en IT
=====================================================

""",
    'data': [
             #'data/account_journal_data.xml',
             'data/tipo_comprobante_data.xml',
             'security/ir.model.access.csv',
             'views/account_invoice_view.xml',
             'views/res_company.xml',
             'views/afip_ncm_view.xml',
             'views/afip_session_view.xml',
             'views/product_view.xml',
             'views/tipo_comprobante_view.xml',
             #'data/afip_error_data.xml'
            ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
