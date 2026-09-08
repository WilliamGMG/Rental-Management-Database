# Rental Management Database

A Python and MariaDB rental management application that supports customers, inventory, rentals, rental history, and item waitlists through a relational database.

## Project Overview

This project demonstrates the database layer behind a rental-management system. The application stores and retrieves customer, item, rental, address, inventory, and waitlist information through MariaDB while exposing that data to the surrounding Python application.

My implementation is contained in [`db_handler.py`](https://github.com/WilliamGMG/Rental-Management-Database/blob/main/db_handler.py), where I developed the application's **database-access and persistence layer**.

My work focused on translating application operations into SQL and coordinating Python objects with a normalized relational database. This included implementing database inserts and updates, multi-table customer operations, rental lifecycle workflows, dynamic search queries, waitlist management, inventory calculations, transaction persistence, and conversion between SQL query results and application objects.

The remaining files provide the surrounding application structure that interacts with this database layer.

## Key Contributions

Through `db_handler.py`, I implemented:

* **Python–MariaDB integration** for persistent application data
* **Parameterized SQL queries** for inserts, updates, searches, and deletes
* **Dynamic SQL query construction** based on optional user-provided filters
* **Normalized relational data handling** across related customer and address tables
* **SQL joins and subqueries** for accessing and modifying related records
* **Partial record updates** that modify only fields explicitly changed by the user
* **Rental lifecycle management**, including creation, extensions, returns, and rental history
* **Waitlist logic** for assigning, querying, and advancing customer positions
* **Real-time inventory calculations** based on owned copies and active rentals
* **Python object mapping** from relational query results into application-level objects
* **Transaction persistence and database resource management** using commits, cursor cleanup, and connection cleanup

## Database Integration

`db_handler.py` establishes and manages the application's connection to MariaDB using configured database credentials and a persistent cursor.

Database operations use **parameterized SQL statements**, keeping user-supplied values separate from SQL query text rather than directly embedding input into statements.

The implementation also manages transaction persistence and database resources through:

* `conn.commit()` for explicitly persisting database changes
* Cursor cleanup
* MariaDB connection cleanup

## Item Management

Implemented item creation and retrieval operations against the item data stored in MariaDB.

Item creation:

* Generates a new surrogate key based on existing table data
* Inserts item attributes using a parameterized `INSERT`
* Persists the transaction to the database

Search results are converted from relational database rows back into the application's custom Python `Item` objects.

### Dynamic Item Search

Item searches support combinations of optional criteria including:

* Minimum price
* Maximum price
* Start-year ranges
* Exact attribute matching
* Partial text matching with SQL `LIKE`

Instead of maintaining a separate SQL statement for every possible combination of filters, the query is constructed dynamically. Only active search criteria are added to the `WHERE` clause, while a corresponding parameter list is built alongside it.

Multiple selected conditions are combined using `AND`.

## Customer Management

Customer creation coordinates data across the normalized `customer` and `customer_address` tables.

The implementation:

* Splits customer names into first and last names
* Parses structured street addresses with regular expressions
* Separates address information into individual database fields
* Generates new address surrogate keys
* Inserts customer and address records
* Associates each customer with the corresponding address record

### Partial Customer Updates

Customer records can be updated without overwriting fields that were not changed.

`db_handler.py` dynamically constructs the SQL `SET` clause so that only fields supplied by the user are included in the resulting `UPDATE`.

Because address information exists in a related table rather than directly inside the customer table, address updates are handled separately through a SQL subquery targeting the customer's associated address record.

### Customer Search

Customer filtering operates across both customer and address information using an `INNER JOIN` between the normalized tables.

Supported filters include:

* Customer ID
* First and last name
* Email
* Individual address fields
* Exact matches
* Pattern-based matches

Rows returned from the joined relational query are reconstructed into higher-level Python `Customer` objects.

## Rental Management

Implemented database operations for creating, extending, returning, and querying rentals.

### Creating Rentals

New rentals use Python date handling to calculate their due dates automatically.

When a rental is created:

1. The current rental date is established.
2. `timedelta` logic calculates a due date 14 days later.
3. The rental information is inserted into the active rental table.
4. The transaction is committed to MariaDB.

### Extending Rentals

Existing rentals can be extended directly in the database using MariaDB date arithmetic.

An extension adds **14 days** to the rental's existing due date rather than recalculating the date externally.

### Returning Items

Returning an item moves the transaction from active rental data into rental history.

The return workflow:

1. Retrieves the corresponding active rental.
2. Records the current return date.
3. Inserts the completed transaction into the rental-history table.
4. Deletes the corresponding record from the active-rental table.
5. Commits the changes.

Separating current rentals from rental history preserves completed transaction records while keeping active-rental queries focused on items that are still checked out.

## Rental Search

Dynamic rental queries support optional filtering by:

* Item
* Customer
* Rental-date ranges
* Due-date ranges

Database rows returned by these queries are converted into custom Python `Rental` objects.

## Rental History

Historical rental searches support:

* Rental-date ranges
* Due-date ranges
* Return-date ranges

Results are reconstructed into custom `RentalHistory` objects for use by the application.

## Waitlist Management

The database layer implements both waitlist modification and search operations.

### Joining a Waitlist

When a customer is added to an item's waitlist, the application:

1. Queries the current maximum waitlist position for that item.
2. Determines the next available position.
3. Inserts the customer at that position.

### Advancing a Waitlist

When the first customer is removed, the waitlist is advanced by:

1. Deleting the customer in the first position.
2. Decrementing the remaining customers' positions.

This keeps waitlist positions sequential after the first entry has been removed.

### Waitlist Queries

Dynamic waitlist searches support filtering by:

* Customer
* Item
* Exact position
* Position ranges

Returned rows are converted into custom Python `Waitlist` objects.

Additional database operations provide:

* A customer's current waitlist position for a specific item
* Waitlist length using SQL `COUNT(*)`

## Real-Time Inventory

Available inventory is calculated from current database state rather than stored as a separate static value.

The application queries:

* The total number of copies owned
* The number of currently active rentals

Available inventory is calculated as:

```text
available inventory = total copies owned - active rentals
```

This allows availability to reflect the active rental records currently stored in the database.

Nonexistent item lookups are handled explicitly with a sentinel return value so that the application can distinguish between an unavailable item and an item that does not exist.

## Data-Access Layer

A central responsibility of `db_handler.py` is coordinating the application's Python object model with its relational database representation.

The implementation converts between MariaDB rows and application objects including:

* `Item`
* `Customer`
* `Rental`
* `RentalHistory`
* `Waitlist`

This concentrates database-specific query logic inside the data-access layer while allowing the surrounding application to work with higher-level Python objects.

## Technologies and Concepts

* Python
* MariaDB
* SQL
* Parameterized queries
* Relational database operations
* Normalized database tables
* `INNER JOIN`
* SQL subqueries
* Dynamic `WHERE` clause construction
* Dynamic `SET` clause construction
* SQL `LIKE` pattern matching
* Aggregate queries with `COUNT(*)`
* MariaDB date arithmetic
* Python `date` and `timedelta`
* Regular-expression parsing
* Object-to-relational data mapping
* Transaction management
* Database cursor and connection management
