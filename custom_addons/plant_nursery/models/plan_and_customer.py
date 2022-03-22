from odoo import fields, models, api
from odoo.exceptions import UserError

CONFIRM_STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirmed'),
    ('cancel', 'Canceled'),
]

SOLD_STATE = [
    ('sold', 'Sold'),
]

class PlantCategory(models.Model):
    _name = "nursery.category"
    _description = "Nusery plant category table"

    name = fields.Char()
    description = fields.Char('Description of this type of fruit')
    # One2many field is automatically displayed as a list. Odoo chooses the right ‘widget’ depending on the field type.
    plant_ids = fields.One2many("nursery.plant", "category_id")

class Plant(models.Model):
    _name = "nursery.plant"
    _description = "Nusery plant table"
    _order = "sequence, name asc"

    category_id = fields.Many2one("nursery.category")
    name = fields.Char('Plant Name', required=True)
    price = fields.Float('Plant price', required=True)
    # one plant can have many order, only for reference from view, not store in DB
    # Because a One2many is a virtual relationship, there must be a Many2one field defined in the comodel.
    # We defined on our order model a link to the nursery.order model thanks to the field plant_id
    # We can define the inverse relation, i.e. the list of order models linked to our plant
    order_ids = fields.One2many("nursery.order", "plant_id", string="Orders")
    order_count = fields.Integer(
        compute='_compute_order_count',
        # Do you wanna store this field in DB, default is False
        # You need to store this field in DB in order to make _check_available_in_stock work correctly
        store=True,
        string="Total sold")
    number_in_stock = fields.Integer()
    image = fields.Binary("Plant Image", attachment=True)
    # manual ordering
    sequence = fields.Integer('Sequence', default=1, help="Used to order stages. Lower is better.")
    order_custom_ids = fields.Many2many("order.custom")

    # computed fields, mostly this field is read-only, but you can use inverse function to set value to it
    # trigger after every creation or modification, instead of overriding create & write
    # Every time the plant.order_ids is changed, the plant.order_count is automatically recomputed for all the records referring to it!
    # this is private method
    @api.depends('order_custom_ids')
    def _compute_order_count(self):
        # The object self is a recordset, i.e. an ordered collection of records.
        # Depend on which view we are working on, self will represent for one or all record in DB
        # Also note that we loop on self. Always assume that a method can be called on multiple records; it’s better for reusability.
        for plant in self:
            plant.order_count = len(plant.order_custom_ids)

    # The constraint is automatically evaluated when any of these fields are modified
    # Need field below be stored in DB in order to work correctly
    @api.constrains('order_count', 'number_in_stock')
    def _check_available_in_stock(self):
        for plant in self:
            if plant.number_in_stock and plant.order_count > plant.number_in_stock:
                raise UserError(f"There is only {plant.number_in_stock} {plant.name} in stock, but {plant.order_count} were sold!")
    
    def increase_number_in_stock(self):
        for record in self:
            record.number_in_stock += 1
        return True


class Customer(models.Model):
    _name = "nursery.customer"
    _description = "Customer table"
    _order = "name asc"

    name = fields.Char('Customer Name', required=True)
    email = fields.Char('Customer email', required=True)
    image = fields.Binary("Customer Image", attachment=True)


class Order(models.Model):
    _name = "nursery.order"
    _description = "Order table"
    _order = "id asc"

    date_crate = fields.Datetime(default=fields.Datetime.now)
    # many order can have one plant_id, same with Foreign key
    # you can refer to plant through Order
    plant_id = fields.Many2one("nursery.plant", required=True)
    # many order can have one customer_id
    # you can refer to customer through Order
    customer_id = fields.Many2one("nursery.customer")

    # confirm_state = fields.Selection(CONFIRM_STATE, default='draft')
    # sold_state = fields.Selection(SOLD_STATE, default='sold')
    # state_choise = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('sold', 'Sold'),
    # ], default='draft')
    
    # @api.depends('state_choise')
    # def _compute_state(self):
    #     for order in self:
    #         if order.state_choise == 'draft':
    #             order.state = order.confirm_state
    #         else:
    #             order.state = order.sold_state

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('sold', 'Sold'),
        ('cancel', 'Canceled'),
    ], default='draft')

    last_modification = fields.Datetime(readonly=True)

    # overide the write method of Model
    def write(self, values):
        # helper to "YYYY-MM-DD"
        # add current datetime whenever create a new record
        values['last_modification'] = fields.Datetime.now()

        return super(Order, self).write(values)

    def unlink(self):
        # self can be a record or record set, by coding this way, we can work on both cases
        for order in self:
            if order.state == 'confirm':
                raise UserError("You can not delete confirmed orders")
        
        return super(Order, self).unlink()

    def sold(self):
        self.state = 'sold'
        self.env["invoicing.custom"].create(
                {
                    "order_id": self.id,
                    "customer_name": self.customer_id.name,
                    "plant_name": self.plant_id.name,
                    "plant_price": self.plant_id.price
                }
            )
        return True    


class OrderCustom(models.Model):
    _name = "order.custom"
    _description = "Order that contain multiple plant"

    date_crate = fields.Datetime(default=fields.Datetime.now)
    plant_ids = fields.Many2many("nursery.plant", required=True)
    customer_id = fields.Many2one("nursery.customer")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('sold', 'Sold'),
        ('cancel', 'Canceled'),
    ], default='draft')

    last_modification = fields.Datetime(readonly=True)
    order_items = fields.One2many("order.item", "order_id", string="Order Items")

    def sold(self):
        total = 0
        self.state = 'sold'
        plant_names = ''.join([plant.name + ', ' for plant in self.plant_ids])
        plant_names = plant_names[:-2]
        for plant in self.plant_ids:
            total += plant.price

        self.env["invoicing.custom"].create(
                {
                    "order_id": self.id,
                    "customer_name": self.customer_id.name,
                    "plant_names": plant_names,
                    "total": total,
                }
            )
        return True  


class OrderItem(models.Model):
    _name = "order.item"
    _description = "Order items"

    plant_id = fields.Many2one("nursery.plant", required=True)
    order_id = fields.Many2one("order.custom", require=True)
    quantity = fields.Integer("Quantity of plant")

