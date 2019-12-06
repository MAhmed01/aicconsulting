from io import BytesIO
import base64
from odoo import api, fields, models, _

class SaleInvoiceExcelReportWiz(models.TransientModel):

    _name= "sale.invoice.excel.report.wiz"

    report_excel_file = fields.Binary('Dowload report Excel')
    report_file_name = fields.Char('Excel File', size=64)
