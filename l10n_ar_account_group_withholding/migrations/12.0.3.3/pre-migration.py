# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
_logger = logging.getLogger(__name__)

def create_column_table(cr):
    _logger.info('AAAA')
    cr.execute("""ALTER TABLE account_withholding ADD COLUMN payment INTEGER""")
    cr.execute("""UPDATE account_withholding SET payment=payment_id""")
    cr.execute("""ALTER TABLE account_withholding ALTER COLUMN payment_id DROP NOT NULL""")
    cr.execute("""UPDATE account_withholding SET payment_id=NULL""")


def migrate(cr, version):
    create_column_table(cr)
