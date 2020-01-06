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
    'name': 'Libros Fiscales AITIC',
        'version': '10.0.0.1.0',
    'author': "AITIC",
    'maintainer': 'AITIC',
    'website': 'http://www.aitic.com.ar',
    'license': 'AGPL-3',
    'category': 'Localization/Arqentina',
    'summary': 'Libros de Compra/Venta Argentina',
    'depends': ['l10n_ar_facturae'],
    'description': """
Libros de Compra / Venta
===========================================================================
1-. Libros Venta / Compra\n
2-. Exportación de Libros\n

AITIC - Asesoría Integral en IT
=====================================================
        """,
    'data': [
        'security/ir.model.access.csv',
        'report/report_book.xml',
        'report/account_report.xml',
        'views/account_book_view.xml',
        'views/condicion_venta_view.xml',
        'views/tipo_comprobante_view.xml',
        'security/groups.xml',
    ],
    'external_dependencies': {
        'python': ['calendar','csv','base64','xlwt','io'],
     },
    'installable': True,
    'auto_install': False,
    'demo': [],
    'test': [],
}

