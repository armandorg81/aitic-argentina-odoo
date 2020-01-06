# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
_logger = logging.getLogger(__name__)

def create_column_table(cr):
    cr.execute("""ALTER TABLE account_payment_group ADD COLUMN withholding_agip_aliquot_aux DOUBLE PRECISION""")
    cr.execute("""UPDATE account_payment_group SET withholding_agip_aliquot_aux=withholding_agip_aliquot""")


def migrate(cr, version, use_env=True):
    create_column_table(cr)