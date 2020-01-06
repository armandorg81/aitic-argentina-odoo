# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
_logger = logging.getLogger(__name__)

def create_withholding(cr):
    cr.execute("""SELECT id FROM account_payment_group""")
    for x in cr.fetchall():
        cr.execute("""SELECT move_line_id, payment_group_advance_amount, currency_id 
                           FROM payment_group_advance_move WHERE payment_group_id = %s""" % (x[0]))
        for y in cr.fetchall():
            cr.execute("""SELECT invoice_id FROM account_move_line WHERE id = %s AND invoice_id > 0 """ % (y[0]))
            invoice = cr.fetchone()[0]
            cr.execute("""SELECT number, partner_id, date, num_comprobante, tipo_comprobante,
                            currency_id, company_id
                            FROM account_invoice WHERE id = %s""" % (invoice))
            date_invoice = cr.fetchone()
            cr.execute("""SELECT currency_id FROM res_company WHERE id = %s""" % (date_invoice[6]))
            company_currency_id = cr.fetchone()[0]
            amount = y[1] if y[1] > 0.0 else y[1] * -1
            cr.execute("""INSERT INTO account_invoice_group(invoice_id, payment_group_id, number, currency_id, 
                            company_id, company_currency_id, advance_amount)
                            VALUES (%s, %s, '%s', %s, %s, %s, %s);""" % (
                            invoice, x[0], date_invoice[0], date_invoice[5], date_invoice[6], company_currency_id, amount))

def migrate(cr, version):
    create_withholding(cr)
