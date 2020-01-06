# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
_logger = logging.getLogger(__name__)

def create_withholding(cr):
    cr.execute("""SELECT
                id, amount_agip_withholding, withholding_tax_base_real, date, partner_id, name, withholding_agip_aliquot_aux
                FROM account_payment_group WHERE amount_agip_withholding > 0.0""")
    i = 1
    for x in cr.fetchall():
        cr.execute("""SELECT id FROM account_payment 
                                            WHERE payment_group_id = %s and type_aliquot = 'agip'""" % (x[0]))
        payment = cr.fetchone()[0]
        name = str(i).zfill(8)
        cr.execute("""INSERT INTO account_withholding(name, date, reference, partner_id, payment_id, 
                                withholding_amount, withholding_tax_base_real, state, type_aliquot, withholding_agip_aliquot)
                                VALUES ('%s', '%s', '%s', %s, %s, %s, %s, '%s', '%s', %s);""" % (
                                name, x[3], x[5], x[4], payment, x[1], x[2], 'done', 'agip', x[6]))
        i += 1

def delete_column_table(cr):
    cr.execute("""ALTER TABLE account_payment_group DROP COLUMN withholding_agip_aliquot_aux""")


def migrate(cr, version):
    create_withholding(cr)
    delete_column_table(cr)
