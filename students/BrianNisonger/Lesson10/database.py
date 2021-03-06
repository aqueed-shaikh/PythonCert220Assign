import os
import csv
import logging
import pymongo
import time
import types
import os

records_db = {}


class MongoDBConnection():
    def __init__(self, host='127.0.0.1', port=27017):
        self.host = host
        self.port = port
        self.connection = None

    def __enter__(self):
        try:
            self.connection = pymongo.MongoClient(self.host, self.port)
        except pymongo.errors.ConfigurationError:
            logging.error("Invalid Configuration")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logging.error("Errors in connection")
        else:
            self.connection.close()


def time_func(func):
    """
    Function to time stuff
    """

    def decorated_func(*args, **kwargs):
        start = time.time()
        returned_value = func(*args, **kwargs)
        end = time.time()
        total_time = end - start
        if total_time > 0:
            time_str = f'{func.__name__},{total_time},{records_db[func.__name__]}\n'
            with open("timing.csv", "a") as file:
                file.write(time_str)
        return returned_value

    return decorated_func


class Time_stuff(type):
    def __new__(cls, name, bases, attr):
        for name, value in attr.items():
            if type(value) is types.FunctionType or type(
                    value) is types.MethodType:
                attr[name] = time_func(value)

        return super(Time_stuff, cls).__new__(cls, name, bases, attr)


class Database(metaclass=Time_stuff):
    def calculate_availability(product_list, rental_list):
        for product in product_list:
            count = 0
            for rental in rental_list:
                if rental["product_id"] == product["product_id"]:
                    count += 1
            product_available = int(product["quantity_available"]) - count
            product["quantity_available"] = product_available
            records_db['calculate_availability'] = 0
        return product_list

    def make_product_dict(prod_available_list):
        fields = ["description", "product_type", "quantity_available"]
        product_values_dict = {}
        product_dict = {}
        for product in prod_available_list:
            product_values_dict = {}
            for field in fields:
                product_values_dict[field] = product[field]
            if product["quantity_available"] > 0:
                product_dict[product["product_id"]] = product_values_dict
                records_db['make_product_dict'] = 0
        return product_dict

    def return_user_ids(rental_list):
        records_db['return_user_ids'] = 0
        return [rental["user_id"] for rental in rental_list]

    def make_customer_dict(user_list):
        fields = ["name", "address", "phone_number", "email"]
        customer_values_dict = {}
        customer_dict = {}
        for customer in user_list:
            customer_values_dict = {}
            for field in fields:
                customer_values_dict[field] = customer[field]
                customer_dict[customer["user_id"]] = customer_values_dict
                records_db['make_customer_dict'] = 0
        return customer_dict

    def import_data(directory, filename):
        mongo = MongoDBConnection()
        with mongo:
            db = mongo.connection.furniture
            added_count_list = []
            error_count_list = []
            file = filename
            with open(os.path.join(directory, file)) as csv_file:
                csv_dict = csv.DictReader(csv_file, delimiter=',')
                collection = db[file.replace(".csv", "")]
                try:
                    result = collection.insert_many(csv_dict)
                    added_count_list.append(len(result.inserted_ids))
                    error_count_list.append(0)
                except BulkWriteError as bwe:
                    error_count_list.append(1)
                    logging.error(bwe)
        records_db['import_data'] = added_count_list[0]
        return (added_count_list[0], error_count_list[0])

    def show_available_products():
        mongo = MongoDBConnection()
        with mongo:
            db = mongo.connection.furniture
            product_collection = db["product_data"]
            rental_collection = db["rental_data"]
            product_list = list(product_collection.find())
            rental_list = list(rental_collection.find())
            product_available_list = Database.calculate_availability(
                product_list, rental_list)
            product_dict = Database.make_product_dict(product_available_list)
            records_db['show_available_products'] = len(product_list) + len(
                rental_list)
            return product_dict

    def show_rentals(prod_id):
        mongo = MongoDBConnection()
        user_list = []
        with mongo:
            db = mongo.connection.furniture
            rental_collection = db["rental_data"]
            customer_collection = db["customer_data"]
            rental_list = list(rental_collection.find({"product_id": prod_id}))
            users = Database.return_user_ids(rental_list)
            for user in users:
                user_list.append(
                    customer_collection.find_one({
                        'user_id': user
                    }))
            customer_dict = Database.make_customer_dict(user_list)
            records_db['show_rentals'] = len(rental_list) + len(users)
        return customer_dict