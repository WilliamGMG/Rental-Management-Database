from MARIADB_CREDS import DB_CONFIG
from mariadb import connect
from models.RentalHistory import RentalHistory
from models.Waitlist import Waitlist
from models.Item import Item
from models.Rental import Rental
from models.Customer import Customer
from datetime import date, timedelta
import re

conn = connect(user=DB_CONFIG["username"], password=DB_CONFIG["password"], host=DB_CONFIG["host"],
               database=DB_CONFIG["database"], port=DB_CONFIG["port"])

cur = conn.cursor()


def add_item(new_item: Item = None):
    """
    new_item - An Item object containing a new item to be inserted into the DB in the item table.
        new_item and its attributes will never be None.
    """
    query = "INSERT INTO item " \
            "(i_item_sk, i_item_id, i_rec_start_date, i_product_name, i_brand, i_class, i_category, i_manufact, i_current_price, i_num_owned) " \
            "VALUES(((SELECT MAX(i_item_sk) FROM item) + 1), ?, ?, ?, ?, NULL, ?, ?, ?, ?)"

    cur.execute(query, (
    new_item.item_id, f"{new_item.start_year}-01-01", new_item.product_name, new_item.brand, new_item.category,
    new_item.manufact, new_item.current_price, new_item.num_owned))


def add_customer(new_customer: Customer = None):
    """
    new_customer - A Customer object containing a new customer to be inserted into the DB in the customer table.
        new_customer and its attributes will never be None.
    """
    # Breaks apart the address string into the 5 peices we need
    re_addr_pattern = "([^ ]+) ([^,]+), ([^,]+), ([^ ]+) ([^ ]+)"
    match = re.match(re_addr_pattern, new_customer.address)

    cur.execute("SELECT MAX(ca_address_sk) FROM customer_address")
    addrMax = cur.fetchone()[0]
    new_addr_sk = 1 if addrMax == None else addrMax + 1

    addr_query = "INSERT INTO customer_address " \
                 "(ca_address_sk, ca_street_number, ca_street_name, ca_city, ca_state, ca_zip) " \
                 "VALUES(?, ?, ?, ?, ?, ?)"
    cur.execute(addr_query,
                (new_addr_sk, match.group(1), match.group(2), match.group(3), match.group(4), match.group(5)))

    name_parts = new_customer.name.split(" ", 1)
    first_name = name_parts[0]
    last_name  = name_parts[1] if len(name_parts) > 1 else ""

    # Insert the customer using the addr sk we just made above
    cust_query = "INSERT INTO customer " \
                 "(c_customer_sk, c_customer_id, c_first_name, c_last_name, c_email_address, c_current_addr_sk) " \
                 "VALUES(((SELECT MAX(c_customer_sk) FROM customer) + 1), ?, ?, ?, ?, ?)"
    cur.execute(cust_query, (new_customer.customer_id, first_name, last_name, new_customer.email, new_addr_sk))


def edit_customer(original_customer_id: str = None, new_customer: Customer = None):
    """
    original_customer_id - A string containing the customer id for the customer to be edited.
    new_customer - A Customer object containing attributes to update. If an attribute is None, it should not be altered.
    """

    # build up the update query peice by peice depending on which fields were given
    set_clauses = []
    params = []

    if (new_customer.customer_id != None):
        set_clauses.append("c_customer_id = ?")
        params.append(new_customer.customer_id)

    if (new_customer.name != None):
        nameParts = new_customer.name.split(" ", 1)
        first_name = nameParts[0]
        last_name = nameParts[1] if len(nameParts) > 1 else ""
        set_clauses.append("c_first_name = ?")
        params.append(first_name)
        set_clauses.append("c_last_name = ?")
        params.append(last_name)


    if (new_customer.email != None):
        set_clauses.append("c_email_address = ?")
        params.append(new_customer.email)

    if (len(set_clauses) > 0):
        params.append(original_customer_id)
        query = f"UPDATE customer SET {', '.join(set_clauses)} WHERE c_customer_id = ?"
        cur.execute(query, params)

    # address lives in a different table so we have to update it seperatly
    if (new_customer.address != None):
        re_addr_pattern = "([^ ]+) ([^,]+), ([^,]+), ([^ ]+) ([^ ]+)"
        match = re.match(re_addr_pattern, new_customer.address)

        lookup_id = new_customer.customer_id if new_customer.customer_id != None else original_customer_id

        addr_query = "UPDATE customer_address " \
                     "SET ca_street_number = ?, ca_street_name = ?, ca_city = ?, ca_state = ?, ca_zip = ? " \
                     "WHERE ca_address_sk = (SELECT c_current_addr_sk FROM customer WHERE c_customer_id = ?)"
        cur.execute(addr_query,
                    (match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), lookup_id))


def rent_item(item_id: str = None, customer_id: str = None):
    """
    item_id - A string containing the Item ID for the item being rented.
    customer_id - A string containing the customer id of the customer renting the item.
    """
    today = date.today()
    dueDate = today + timedelta(days=14)
    query = "INSERT INTO rental(item_id, customer_id, rental_date, due_date) VALUES(?, ?, ?, ?)"
    cur.execute(query, (item_id, customer_id, today, dueDate))


def waitlist_customer(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's new place in line.
    """

    cur.execute("SELECT MAX(place_in_line) FROM waitlist WHERE item_id = ?", (item_id,))
    place_in_line = cur.fetchone()[0]
    place_in_line = 1 if not place_in_line else place_in_line + 1

    query = "INSERT INTO waitlist(item_id, customer_id, place_in_line) VALUES(?, ?, ?)"
    cur.execute(query, (item_id, customer_id, place_in_line))

    return place_in_line


def update_waitlist(item_id: str = None):
    """
    Removes person at position 1 and shifts everyone else down by 1.
    """

    cur.execute("DELETE FROM waitlist WHERE place_in_line = 1 AND item_id = ?", (item_id,))
    cur.execute("UPDATE waitlist SET place_in_line = place_in_line - 1 WHERE item_id = ?", (item_id,))


def return_item(item_id: str = None, customer_id: str = None):
    """
    Moves a rental from rental to rental_history with return_date = today.
    """
    today = date.today()
    cur.execute("SELECT rental_date, due_date FROM rental WHERE item_id = ? AND customer_id = ?",
                (item_id, customer_id))
    row = cur.fetchone()
    if (row == None):
        return

    rentalDate, due_date = row
    insert_query = "INSERT INTO rental_history" \
                   "(item_id, customer_id, rental_date, due_date, return_date) " \
                   "VALUES(?, ?, ?, ?, ?)"
    cur.execute(insert_query, (item_id, customer_id, rentalDate, due_date, today))
    cur.execute("DELETE FROM rental WHERE item_id = ? AND customer_id = ?", (item_id, customer_id))


def grant_extension(item_id: str = None, customer_id: str = None):
    """
    Adds 14 days to the due_date.
    """
    query = "UPDATE rental SET due_date = DATE_ADD(due_date, INTERVAL 14 DAY) " \
            "WHERE item_id = ? AND customer_id = ?"
    cur.execute(query, (item_id, customer_id))


def get_filtered_items(filter_attributes: Item = None,
                       use_patterns: bool = False,
                       min_price: float = -1,
                       max_price: float = -1,
                       min_start_year: int = -1,
                       max_start_year: int = -1) -> list[Item]:
    """
    Returns a list of Item objects matching the filters.
    """

    # Collect conditions and parameters for the condtions
    conditions = []
    params = []
    if (min_price != -1):
        conditions.append(f"i_current_price >= ?")
        params.append(min_price)
    if (max_price != -1):
        conditions.append(f"i_current_price <= ?")
        params.append(max_price)
    if (min_start_year != -1):
        conditions.append(f"YEAR(i_rec_start_date) >= ?")
        params.append(min_start_year)
    if (max_start_year != -1):
        conditions.append(f"YEAR(i_rec_start_date) <= ?")
        params.append(max_start_year)

    if (filter_attributes):
        str_comp = "LIKE" if use_patterns else "="
        if (filter_attributes.item_id):
            conditions.append(f"i_item_id {str_comp} ?")
            params.append(filter_attributes.item_id)
        if (filter_attributes.product_name):
            conditions.append(f"i_product_name {str_comp} ?")
            params.append(filter_attributes.product_name)
        if (filter_attributes.brand):
            conditions.append(f"i_brand {str_comp} ?")
            params.append(filter_attributes.brand)
        if (filter_attributes.category):
            conditions.append(f"i_category {str_comp} ?")
            params.append(filter_attributes.category)
        if (filter_attributes.manufact):
            conditions.append(f"i_manufact {str_comp} ?")
            params.append(filter_attributes.manufact)
        if (filter_attributes.current_price != -1):
            conditions.append(f"i_current_price = ?")
            params.append(filter_attributes.current_price)
        if (filter_attributes.start_year != -1):
            conditions.append(f"YEAR(i_rec_start_date) = ?")
            params.append(filter_attributes.start_year)
        if (filter_attributes.num_owned != -1):
            conditions.append(f"i_num_owned = ?")
            params.append(filter_attributes.num_owned)

    # Add up condtions
    condition = f"WHERE {conditions.pop(0)}" if len(conditions) > 0 else ""
    if len(conditions) > 0:
        for c in conditions:
            condition += f" AND {c}"

    query = f"SELECT i_item_id, i_product_name, i_brand, i_category, i_manufact, i_current_price, YEAR(i_rec_start_date), i_num_owned FROM item {condition}"
    cur.execute(query, params)

    # Get info out of cursor into classes
    items = []
    for i in cur:
        items.append(Item(item_id=i[0].strip(), product_name=i[1].strip(), brand=i[2].strip(), category=i[3].strip(),
                          manufact=i[4].strip(), current_price=i[5], start_year=i[6],
                          num_owned=i[7]))

    return items


def get_filtered_customers(filter_attributes: Customer = None, use_patterns: bool = False) -> list[Customer]:
    """
    Returns a list of Customer objects matching the filters.
    """
    re_addr_pattern = "([^ ]+) ([^,]+), ([^,]+), ([^ ]+) ([^ ]+)"

    # Collect conditions and parameters for the condtions
    conditions = []
    params = []
    if filter_attributes:
        str_comp = "LIKE" if use_patterns else "="
        if (filter_attributes.customer_id):
            conditions.append(f"c.c_customer_id {str_comp} ?")
            params.append(filter_attributes.customer_id)
        if (filter_attributes.name):
            conditions.append(f"CONCAT(c.c_first_name, ' ', c.c_last_name) {str_comp} ?")
            params.append(filter_attributes.name)
        if (filter_attributes.email):
            conditions.append(f"c.c_email_address {str_comp} ?")
            params.append(filter_attributes.email)
        if (filter_attributes.address):
            # Decompose the address into parts
            match = re.match(re_addr_pattern, filter_attributes.address)
            conditions.append(f"ca.ca_street_number {str_comp} ?")
            conditions.append(f"ca.ca_street_name {str_comp} ?")
            conditions.append(f"ca.ca_city {str_comp} ?")
            conditions.append(f"ca.ca_state {str_comp} ?")
            conditions.append(f"ca.ca_zip {str_comp} ?")
            params.append(match.group(1))
            params.append(match.group(2))
            params.append(match.group(3))
            params.append(match.group(4))
            params.append(match.group(5))

    # Add up condtions
    condition = f" WHERE {conditions.pop(0)}" if len(conditions) > 0 else ""
    if len(conditions) > 0:
        for c in conditions:
            condition += f" AND {c}"

    query = f"SELECT c.c_customer_id, c.c_first_name, c.c_last_name, ca.ca_street_number, ca.ca_street_name, ca.ca_city, ca.ca_state, ca.ca_zip, c.c_email_address FROM (customer c INNER JOIN customer_address ca ON c.c_current_addr_sk = ca.ca_address_sk) {condition}"
    cur.execute(query, params)

    # Get info out of cursor into classes
    customers = []
    for i in cur:
        customers.append(Customer(customer_id=i[0].strip(), name=f"{i[1].strip()} {i[2].strip()}",
                                  address=f"{i[3].strip()} {i[4].strip()}, {i[5].strip()}, {i[6].strip()} {i[7].strip()}",
                                  email=i[8].strip()))

    return customers


def get_filtered_rentals(filter_attributes: Rental = None,
                         min_rental_date: str = None,
                         max_rental_date: str = None,
                         min_due_date: str = None,
                         max_due_date: str = None) -> list[Rental]:
    """
    Returns a list of Rental objects matching the filters.
    """

    # Collect conditions and parameters for the condtions
    conditions = []
    params = []
    if (min_rental_date):
        conditions.append(f"rental_date >= ?")
        params.append(min_rental_date)
    if (max_rental_date):
        conditions.append(f"rental_date <= ?")
        params.append(max_rental_date)
    if (min_due_date):
        conditions.append(f"due_date >= ?")
        params.append(min_due_date)
    if (max_due_date):
        conditions.append(f"due_date <= ?")
        params.append(max_due_date)

    if (filter_attributes):
        if (filter_attributes.item_id):
            conditions.append(f"item_id = ?")
            params.append(filter_attributes.item_id)
        if (filter_attributes.customer_id):
            conditions.append(f"customer_id = ?")
            params.append(filter_attributes.customer_id)
        if (filter_attributes.rental_date):
            conditions.append(f"rental_date = ?")
            params.append(filter_attributes.rental_date)
        if (filter_attributes.due_date):
            conditions.append(f"due_date = ?")
            params.append(filter_attributes.due_date)

    # Add up condtions
    condition = f" WHERE {conditions.pop(0)}" if len(conditions) > 0 else ""
    if len(conditions) > 0:
        for c in conditions:
            condition += f" AND {c}"

    query = f"SELECT item_id, customer_id, rental_date, due_date FROM rental {condition}"
    cur.execute(query, params)

    # Get info out of cursor into classes
    rentals = []
    for i in cur:
        rentals.append(
            Rental(item_id=i[0].strip(), customer_id=i[1].strip(), rental_date=str(i[2]), due_date=str(i[3])))

    return rentals


def get_filtered_rental_histories(filter_attributes: RentalHistory = None,
                                  min_rental_date: str = None,
                                  max_rental_date: str = None,
                                  min_due_date: str = None,
                                  max_due_date: str = None,
                                  min_return_date: str = None,
                                  max_return_date: str = None) -> list[RentalHistory]:
    """
    Returns a list of RentalHistory objects matching the filters.
    """

    # Collect conditions and parameters for the condtions
    conditions = []
    params = []
    if (min_rental_date):
        conditions.append(f"rental_date >= ?")
        params.append(min_rental_date)
    if (max_rental_date):
        conditions.append(f"rental_date <= ?")
        params.append(max_rental_date)
    if (min_due_date):
        conditions.append(f"due_date >= ?")
        params.append(min_due_date)
    if (max_due_date):
        conditions.append(f"due_date <= ?")
        params.append(max_due_date)
    if (min_return_date):
        conditions.append(f"return_date >= ?")
        params.append(min_return_date)
    if (max_return_date):
        conditions.append(f"return_date <= ?")
        params.append(max_return_date)

    if (filter_attributes):
        if (filter_attributes.item_id):
            conditions.append(f"item_id = ?")
            params.append(filter_attributes.item_id)
        if (filter_attributes.customer_id):
            conditions.append(f"customer_id = ?")
            params.append(filter_attributes.customer_id)
        if (filter_attributes.rental_date):
            conditions.append(f"rental_date = ?")
            params.append(filter_attributes.rental_date)
        if (filter_attributes.due_date):
            conditions.append(f"due_date = ?")
            params.append(filter_attributes.due_date)

    # Add up condtions
    condition = f" WHERE {conditions.pop(0)}" if len(conditions) > 0 else ""
    if len(conditions) > 0:
        for c in conditions:
            condition += f" AND {c}"

    query = f"SELECT item_id, customer_id, rental_date, due_date, return_date FROM rental_history {condition}"
    cur.execute(query, params)

    # Get info out of cursor into classes
    rentals = []
    for i in cur:
        rentals.append(RentalHistory(item_id=i[0].strip(), customer_id=i[1].strip(), rental_date=str(i[2]),
                                     due_date=str(i[3]), return_date=str(i[4])))

    return rentals


def get_filtered_waitlist(filter_attributes: Waitlist = None,
                          min_place_in_line: int = -1,
                          max_place_in_line: int = -1) -> list[Waitlist]:
    """
    Returns a list of Waitlist objects matching the filters.
    """
    # Collect conditions and parameters for the condtions
    conditions = []
    params = []
    if (min_place_in_line != -1):
        conditions.append(f"place_in_line >= ?")
        params.append(min_place_in_line)
    if (max_place_in_line != -1):
        conditions.append(f"place_in_line <= ?")
        params.append(max_place_in_line)

    if (filter_attributes):
        if (filter_attributes.item_id):
            conditions.append(f"item_id = ?")
            params.append(filter_attributes.item_id)
        if (filter_attributes.customer_id):
            conditions.append(f"customer_id = ?")
            params.append(filter_attributes.customer_id)
        if (filter_attributes.place_in_line != -1):
            conditions.append(f"place_in_line = ?")
            params.append(filter_attributes.place_in_line)

    # Add up condtions
    condition = f" WHERE {conditions.pop(0)}" if len(conditions) > 0 else ""
    if len(conditions) > 0:
        for c in conditions:
            condition += f" AND {c}"

    query = f"SELECT item_id, customer_id, place_in_line FROM waitlist {condition}"
    cur.execute(query, params)

    # Get info out of cursor into classes
    waitlist = []
    for i in cur:
        waitlist.append(Waitlist(item_id=i[0].strip(), customer_id=i[1].strip(), place_in_line=i[2]))

    return waitlist


def number_in_stock(item_id: str = None) -> int:
    """
    Returns num_owned - active rentals. Returns -1 if item doesn't exist.
    """
    # Check if item exsists, and if it does how many are owned
    cur.execute("SELECT i_num_owned FROM item WHERE i_item_id = ?", (item_id,))
    row = cur.fetchone()
    if (row == None):
        return -1
    num_owned = row[0]
    # Counts how many copies of this item are currently checked out
    cur.execute("SELECT COUNT(*) FROM rental WHERE item_id = ?", (item_id,))
    rentedOut = cur.fetchone()[0]
    return num_owned - rentedOut


def place_in_line(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's place_in_line, or -1 if not on waitlist.
    """
    cur.execute("SELECT place_in_line FROM waitlist WHERE item_id = ? AND customer_id = ?",
                (item_id, customer_id))
    row = cur.fetchone()
    return row[0] if row != None else -1


def line_length(item_id: str = None) -> int:
    """
    Returns how many people are on the waitlist for this item.
    """
    cur.execute("SELECT COUNT(*) FROM waitlist WHERE item_id = ?", (item_id,))
    return cur.fetchone()[0]


def save_changes():
    """
    Commits all changes made to the db.
    """
    conn.commit()


def close_connection():
    """
    Closes the cursor and connection.
    """

    query = "SELECT * FROM item WHERE i_item_sk=18000"

    cur.execute(query)

    for r in cur:
        print(r)

    cur.close()
    conn.close()