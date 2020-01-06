# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
_logger = logging.getLogger(__name__)

def change_account_withholding(cr):
    cr.execute("""SELECT id, payment FROM account_withholding""")
    for x in cr.fetchall():
        cr.execute("""SELECT id FROM public.account_payment 
                                WHERE payment_group_id = %s and type_aliquot = 'earnings'""" % (x[1]))
        payment = cr.fetchone()[0]
        cr.execute("""SELECT withholding_tax_base_real FROM public.account_payment_group 
                                        WHERE id = %s""" % (x[1]))
        withholding_tax_base_real = cr.fetchone()[0]
        if payment:
            cr.execute("""UPDATE account_withholding SET payment_id=%s, withholding_tax_base_real=%s WHERE id = %s """ % (
                                        payment, x[0], withholding_tax_base_real))

def create_column_table(cr):
    cr.execute("""ALTER TABLE account_withholding DROP COLUMN payment""")


def migrate(cr, version):
    change_account_withholding(cr)
    create_column_table(cr)
