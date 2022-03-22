import json
from odoo import fields, models


class Invoicing(models.Model):
    _name = "invoicing.custom"
    _description = "Custom Invoicing Table"

    order_id = fields.Integer("ID of order")
    customer_name = fields.Char("Name of customer")
    plant_names = fields.Char("Name of plants")
    total = fields.Float("Total price of Plants in this order")

    # def read_custom(self):
    #     for record in self:
    #         customer_obj = record.env["nursery.customer"].search(
    #             [('id', '=', record.customer_id)]
    #         )
    #         if customer_obj:
    #             record.customer_name = customer_obj.name
    #             # used for get data from customer_obj
    #             # print(json.dumps(customer_obj.read(['name', 'email'])))

    #     return True