import pandas as pd
import numpy as np
import os
import time
import dotenv
import ast
import traceback
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union, Optional
from sqlalchemy import create_engine, Engine
from smolagents import (
    ToolCallingAgent,
    OpenAIServerModel,
    tool,
)

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers 
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:    
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################


# Set up and load your env parameters and instantiate your model.
dotenv.load_dotenv(dotenv_path=".env")
openai_api_key = os.getenv("OPENAI_API_KEY")
model = OpenAIServerModel(
    model_id="gpt-4o-mini",
    api_base="https://openai.vocareum.com/v1" if openai_api_key.startswith("voc") else None,
    api_key=openai_api_key,
)

"""Set up tools for your agents to use, these should be methods that combine the database functions above
 and apply criteria to them to ensure that the flow of the system is correct."""


# Tools for inventory agent
item_name_to_matching_product_name: Dict[str, str] = {}

@tool
def find_matching_product_in_inventory(items: List[Dict]) -> List[Dict]:
    """
    Find matching products in inventory 

    Args:
        items (List[Dict]): List of dictionaries representing an item with fields: 
            - item_name (str): The name of an item
            - quantity (int): The quantity needed
            - date_needed (str or datetime): The date when the item is needed in the 'YYYY-MM-DD' format or a datetime object.

    Returns:
        List[Dict]: List of dictionaries mapping the given item names to the matching product names in inventory
            - item_name (str): The name of an item
            - matching_product_name (str): The name of the matching product
            - found (bool): True if a matching product is found, False otherwise
    """

    result: List[Dict] = []
    for item in items:
        item_name, date_needed = item['item_name'], item['date_needed']

        try:
            stocks = get_all_inventory(date_needed)
            words_in_product_names = { product_name: set(product_name.lower().split()) for product_name in stocks }
            words_in_item_name = set(item_name.lower().split())

            max_number_of_common_words = 0
            matching_product_name = ""
            for product_name, words_in_product_name in words_in_product_names.items():
                common_words = words_in_item_name.intersection(words_in_product_name)
                if max_number_of_common_words < len(common_words) and \
                    " ".join(common_words).lower() not in ("", "paper"):
                    matching_product_name = product_name
                    max_number_of_common_words = len(common_words)
                
            if matching_product_name:
                result.append({ 
                    'item_name': item['item_name'],
                    'matching_product_name': matching_product_name,
                    'found': True
                })
                item_name_to_matching_product_name[item['item_name']] = matching_product_name
            else:
                result.append({ 
                    'item_name': item['item_name'],
                    'matching_product_name': "",
                    'found': False
                })
        except Exception as e:
            print(f"Error while looking for a matching product for {item_name}: {str(e)}")
            print(traceback.format_exc())
            result.append({ 
                'item_name': item['item_name'],
                'matching_product_name': "",
                'found': False
            })

    return result

@tool
def is_available_in_inventory(items: List[Dict]) -> List[Dict]:
    """
    Check the availability of items on dates needed

    Args:
        items (List[Dict]): List of dictionaries representing an item with fields: 
            - item_name (str): The name of an item
            - quantity (int): The quantity needed
            - date_needed (str or datetime): The date when the item is needed in the 'YYYY-MM-DD' format or a datetime object.

    Returns:
        List[Dict]: A list of dictionaries containing whether the given item is available:
            - item_name: The name of an item
            - is_available: True if the item is availabe, False otherwise
    """
    
    result: List[Dict] = []
    for item in items:
        if item['item_name'] not in item_name_to_matching_product_name:
            result.append({
                    'item_name': item['item_name'],
                    'is_available': False
                })
            continue

        item_name = item['item_name']
        matching_product_name = item_name_to_matching_product_name[item_name]
        quantity = item['quantity']
        date_needed = item['date_needed']
            
        try:
            stock_info = get_stock_level(matching_product_name, date_needed)
            if (stock_info["item_name"] == matching_product_name).any():
                stock_level = stock_info.loc[stock_info["item_name"] == matching_product_name, "current_stock"]
                result.append({
                    'item_name': item_name,
                    'is_available': stock_level >= quantity
                })
            else:
                result.append({
                    'item_name': item_name,
                    'is_available': False
                })
        except Exception as e:
            print(f"Error while checking if {item_name} is available on {date_needed}: {str(e)}")
            print(traceback.format_exc())
            result.append({ 'item_name': item_name, 'is_available': False })

    return result

# Tools for quoting agent
def find_unit_price(item_name: str) -> float:
    try:
        # Find unit_price from the inventory table
        query = """
        SELECT
            item_name,
            unit_price
        FROM inventory
        WHERE item_name = :item_name
        """
        result = pd.read_sql(query, db_engine, params={"item_name": item_name})
        unit_prices = result.loc[result["item_name"] == item_name, "unit_price"]
        return unit_prices.iloc[0] if not unit_prices.empty else 0.0
    except Exception as e:
        print(f"Error while getting the unit price of {item_name}: {str(e)}")
        print(traceback.format_exc())
        return 0.0

@tool
def get_unit_price() -> Dict[str, float]:
    """
    Find the unit price of a given item

    Returns:
        Dict [str, float]: A dictionary containing the mapping of a given item name to the unit price
            - item_name: unit_price
    """

    result: Dict[str, float] = {}
    for item_name, matching_product_name in item_name_to_matching_product_name.items():
        unit_price = find_unit_price(item_name=matching_product_name)
        if unit_price > 0: 
            result[item_name] = unit_price
    return result

@tool
def find_historical_quotes_with_discount() -> List[str]:
    """
    Retrieve historical quotes with discount

    Returns:
        List[Dict]: List of dictionaries, each representing a quote with discount with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    try:
        search_terms = ["discount"]
        return search_quote_history(search_terms=search_terms)
    except Exception as e:
        print(f"Error while retrieving historical quotes with discount: {str(e)}")
        print(traceback.format_exc())
        return []

@tool
def submit_sale(item_name: str, quantity: int, price: float,date_of_request: Union[str, datetime]) -> str:
    """
    Submit a transaction of sale

    Args:
        item_name (str): The name of an item in the sale
        quantity (int): The quantity of the item in the sale
        price (float): The price of the sale
        date_of_request (str or datetime): The date when the sale is requested in the 'YYYY-MM-DD' format or a datetime object.

    Returns:
        str: Response with transaction id
    """

    if item_name not in item_name_to_matching_product_name:
        return f"Failed to create a transaction of the sale for {item_name} because it does not exist in the system."

    try:
        transaction_id = create_transaction(item_name=item_name_to_matching_product_name[item_name], 
                                            transaction_type='sales', 
                                            quantity=quantity, 
                                            price=price, 
                                            date=date_of_request)
        return f"Created a transaction for the sale of {item_name}: transaction_id={transaction_id}"
    except Exception as e:
        print(f"Error creating a transaction for the sale of {item_name}: {str(e)}")
        print(traceback.format_exc())
        return f"Failed to create a transaction of the sale for {item_name} due to an error."

# Tools for ordering agent
def calculate_supplier_price(item_name: str, quantity: int) -> float:
    # Assume that the item can always be supplied with less price
    unit_price = find_unit_price(item_name=item_name)
    return (0.8 * unit_price) * quantity
    
@tool
def can_be_restocked(item_name: str, quantity: int, date_needed: Union[str, datetime], date_of_request: Union[str, datetime]) -> Dict:
    """
    Check if a given item can be restocked until the given date

    Args:
        item_name (str): The name of an item
        quantity (int): The quantity to restock
        date_needed (str or datetime): The date when the item is needed in the 'YYYY-MM-DD' format or a datetime object.
        date_of_request (str or datetime): The date when the request is made in the 'YYYY-MM-DD' format or a datetime object.

    Returns:
        Dict: A dictionary containing whether the given item can be restocked and the reason
            - restocked: True if an item can be restocked, False otherwise.
            - reason: Reason why an item can or cannot be restocked.
    """

    if item_name not in item_name_to_matching_product_name:
        return {
                "restocked": False,
                "reason": f"We don't provide customers with {item_name}."
            }

    try:
        date_needed_str = date_needed.isoformat() if isinstance(date_needed, datetime) else date_needed
        date_of_request_str = date_of_request.isoformat() if isinstance(date_of_request, datetime) else date_of_request

        supplier_delivery_date_str = get_supplier_delivery_date(input_date_str=date_of_request_str, quantity=quantity)
        supplier_price = calculate_supplier_price(item_name=item_name_to_matching_product_name[item_name], quantity=quantity)
        if supplier_price > 0.0:
            if datetime.fromisoformat(supplier_delivery_date_str) < datetime.fromisoformat(date_needed_str):
                cash_balance = get_cash_balance(as_of_date=date_of_request_str)
                if cash_balance > supplier_price:
                    return { 
                        "restocked": True,
                        "reason": f"{item_name} can be restocked before {date_needed_str}."
                    }
                else:
                    return { 
                        "restocked": False,
                        "reason": f"{item_name} cannot be restocked because the cash balance is not enough to make the purcahse."
                    }
            else:
                return { 
                    "restocked": False,
                    "reason": f"{item_name} cannot be restocked because it cannot be delivered before {date_needed_str}."
                }
        else:
            return {
                "restocked": False,
                "reason": f"We don't provide customers with {item_name}."
            }
    except Exception as e:
        print(f"Error while checking if {item_name} can be restocked until {date_needed}: {str(e)}")
        print(traceback.format_exc())
        return {
            "restocked": False,
            "reason": f"{item_name} cannot be restocked due to a technical issue."
        }

@tool
def submit_order(item_name: str, quantity: int, date_of_request: Union[str, datetime]) -> str:
    """
    Submit a transaction of order

    Args:
        item_name (str): The name of an item in the order
        quantity (int): The quantity of the item in the order
        date_of_request (str or datetime): The date when the order is submitted

    Returns:
        str: Response with transaction id
    """

    if item_name not in item_name_to_matching_product_name:
        return f"Failed to create a transaction for the order of {item_name} because it does not exist in the system."

    try:
        supplier_price = calculate_supplier_price(item_name=item_name_to_matching_product_name[item_name], quantity=quantity)
        if supplier_price > 0.0:
            transaction_id = create_transaction(item_name=item_name_to_matching_product_name[item_name], 
                                                transaction_type='stock_orders', 
                                                quantity=quantity, 
                                                price=supplier_price, 
                                                date=date_of_request)
            return f"Created a transaction for the order of {item_name}: transaction_id={transaction_id}"
        else:
            raise ValueError(f"Cannot find the unit price for {item_name}.")
    except Exception as e:
        print(f"Error creating a transaction for the order of {item_name}: {str(e)}")
        print(traceback.format_exc())
        return f"Failed to create a transaction for the order of {item_name} due to an error."

@tool
def generate_financial_summary(date_of_request: Union[str, datetime]) -> str:
    """
    Generate financial summary to be included in other reports

    Args:
        date_of_request (str or datetime): The date of financial summary in the 'YYYY-MM-DD' format or a datetime object.

    Returns:
        str: Formatted financial summary
    """

    report = generate_financial_report(date_of_request)
    return f"""
    Financial Summary
    DATE: {date_of_request}
    CASH BALANCE: {report["cash_balance"]}
    INVENTORY VALUE: {report["inventory_value"]}
    TOTAL ASSET: {report["total_assets"]}
    """


# Set up your agents and create an orchestration agent that will manage them.
class InventoryAgent(ToolCallingAgent):
    def __init__(self, model):
        super().__init__(
            tools=[find_matching_product_in_inventory, is_available_in_inventory],
            model=model,
            name="inventory_manager",
            description="""
            You are an inventory manager responsible for storage and tracking.
            """
        )


class OrderingAgent(ToolCallingAgent):
    def __init__(self, model):
        super().__init__(
            tools=[can_be_restocked, submit_order],
            model=model,
            name="ordering_manager",
            description="""
            You are an ordering manager responsible for restocking.
            """
        )


class QuotingAgent(ToolCallingAgent):
    def __init__(self, model):
        super().__init__(
            tools=[get_unit_price, find_historical_quotes_with_discount, submit_sale],
            model=model,
            name="quoting_manager",
            description="""
            You are a quoting manager responsible for issuing quotes.
            """
        )


class AccountingAgent(ToolCallingAgent):
    def __init__(self, model):
        super().__init__(
            tools=[generate_financial_summary],
            model=model,
            name="accounting_manager",
            description="""
            You are an accounting manager responsible for financial reporting.
            """
        )


class Orchestrator(ToolCallingAgent):
    """
    Orchestrator that coordinates the multi-agent inventory management and quote system.
    """

    def __init__(self, model):
        self.model = model
        
        self.inventory_agent = InventoryAgent(model=model)
        self.quoting_agent = QuotingAgent(model=model)
        self.ordering_agent = OrderingAgent(model=model)
        self.accounting_agnet = AccountingAgent(model=model)
        
        @tool
        def search_product(items: List[Dict]) -> List[Dict]:
            """
            Find any matching product in inventory

            Args:
                items (List[Dict]): List of dictionaries containing item name, quantity, and request date
                    - item_name (str): The name of an item
                    - quantity (int): The quantity needed
                    - date_needed (str or datetime): The date when the item is needed in the 'YYYY-MM-DD' format or a datetime object.
    
            Returns:
                List[Dict]: List of dictionaries mapping the given item names to the matching product names in inventory
                    - item_name (str): The name of an item
                    - matching_product_name (str): The name of the matching product
                    - found (bool): True if a matching product is found, False otherwise
            """

            task = f"""
            Items: {items}
            
            Use 'find_matching_product_in_inventory' to find a mathing product per item.
            """
            return self.inventory_agent.run(task)
        
        @tool
        def get_items_without_matched_products(items: List[Dict]) -> List:
            """
            Find items without matching products in inventory

            Args:
                items (List[Dict]): List of dictionaries containing item name, quantity, and request date
                    - item_name (str): The name of an item
                    - quantity (int): The quantity needed
                    - date_needed (str or datetime): The date when the item is needed in the 'YYYY-MM-DD' format or a datetime object.
    
            Returns:
                List: item names without matching products
            """

            return [item['item_name'] for item in items if item['item_name'] not in item_name_to_matching_product_name]
        
        @tool
        def check_inventory(items: List[Dict]) -> List[Dict]:
            """
            Check inventory for items

            Args:
                items (List[Dict]): A list of dictionaries containing item name, quantity, and request date
                    - item_name (str): The name of an item
                    - quantity (int): The quantity needed
                    - date_needed (str or datetime): The date when the item is needed in the 'YYYY-MM-DD' format or a datetime object.
    
            Returns:
                Dict: A list of dictionaries containing whether the given item is available:
                    - item_name: The name of an item
                    - is_available: True if the item is availabe, False otherwise
            """

            task = f"""
            Items: {items}
            Matching Products In Inventory: {item_name_to_matching_product_name}

            Use 'is_available_in_inventory' to check the availability of given items on the dates needed.
            Respond using the following format:
                [
                    {{ 'item_name': name1, 'is_available': True or False }},
                    {{ 'item_name': name2, 'is_available': True or False }},
                ]
            """
            return self.inventory_agent.run(task)
        
        @tool
        def order_item(item_name: str, quantity: int, date_needed: Union[str, datetime], date_of_request: Union[str, datetime]) -> Dict:
            """
            Order an item for restock

            Args:
                item_name (str): The name of an item
                quantity (int): The quantity of the item
                date_needed (str or datetime): The date when the item is needed in the 'YYYY-MM-DD' format or a datetime object.
                date_of_request (str or datetime): The date when the request is made in the 'YYYY-MM-DD' format or a datetime object.
    
            Returns:
                Dict: A dictionary containing whether the item can be restocked
                    - item_name
                    - quantity
                    - date_needed
                    - date_of_request
                    - restocked
                    - reason
            """

            task = f"""
            Item: {item_name}
            Quantity: {quantity}
            Date Needed: {date_needed}
            Date Requested: {date_of_request}

            Attempt to restock the matching product for the given item.
            Use 'can_be_restocked' to check if the matching product can be delivered from a supplier before the date needed.
                - If yes, use 'submit_order' to purchase the item.
                - If no, indicate the reason (delivery date or cash balance) in the response.
            Respond using the format shown below:
            {{
                "item_name": Item, 
                "quantity": Quantity, 
                "date_needed": Date,
                "date_of_request": Date, 
                "restocked": True if the item can be restocked, False otherwise,
                "reason": reason why the item can or cannot be restocked
            }}
            """
            return self.ordering_agent.run(task)
        
        @tool
        def is_ready_for_quote(stocked_flags: List[str]) -> bool:
            """
            Check if ready to create a quote

            Args:
                stocked_flags (List[str]]): A list of STOCKED/OUT_OF_STOCK flags:
            
            Returns:
                bool: True if all the flags are STOCKED, False otherwise.
            """

            return all(flag == "STOCKED" for flag in stocked_flags)
        
        @tool
        def create_quote(quote_request: str, date_of_request: Union[str, datetime]) -> Dict:
            """
            Issue a quote for the given request

            Args:
                quote_request (str): Original quote request
                date_of_request (str or datetime): The date of request
    
            Returns:
                Dict: A dictionary containing quote explanation, total amount, and request metadata:
                    - quote_explanation (str)
                    - total_amount (int)
                    - request_metadata (dict)
                        - job_type (str)
                        - order_size (str)
                        - event_type (str)
            """

            try:
                task = f"""
                Request: {quote_request}
                Matching Products In Inventory: {item_name_to_matching_product_name}
                Request Date: {date_of_request}

                For a given quote request, issue a quote following this workflow step-by-step:
                Step 1. Use 'get_unit_price' with the given matching products information to find the unit prices of the items in the request. Calculate prices of individual items based on the unit prices.
                Step 2. Use 'find_historical_quotes_with_discount' to find quotes with discount in the past. Determine if the current request is eligible for discount based on the size of the request as well as its similarity with the past quotes with discount.
                Step 3. Record a transaction per item by using 'submit_sale' with the item name, matching product name, quantity, price, and request date.
                Step 4. Compose detailed explanation:
                    - Include all the item names and quantities from request together with prices
                    - Include the total cost and expected delivery date.
                    - If a discount is applied, mention it in the explanation. Otherwise, do not mention about a discount.
                    - This will be used for the main body of the response. Do not include header or closing.
                    - Do not include any internal information. For example, profit margin or internal system error messages should not appear in the explanation.
                Respond with the following format:
                {{
                    "quote_explanation": "detailed explanation of the quote",
                    "total_amount": "sum of total prices with discount"
                    "request_metadata": {{
                        "job_type": "job title of the quote requester",
                        "order_size": "one of small, medium, and large",
                        "event_type": "type of the event in the quote request"
                    }}
                }}
                """
                return self.quoting_agent.run(task)
            except Exception as e:
                print(f"Error while creating a quote: {str(e)}")
                print(traceback.format_exc())
                return """
                Failed to create a quote due to a technical issue"
                """
        
        @tool
        def generate_summary_report(quote_request: str, quote: Optional[Dict] = None) -> str:
            """
            Create a summary report 

            Args:
                quote_request (str): Original quote request
                quote (Optional): A dictionary containing quote explanation, total amount, and request metadata:
                    - quote_explanation (str)
                    - total_amount (int)
                    - request_metadata (dict)
                        - job_type (str)
                        - order_size (str)
                        - event_type (str)
    
            Returns:
                str: Summary report
            """

            task = f"""
            Request: {quote_request}
            Quote: {quote or "Not Quoted"}

            Generate a summary report based on the given request and quote. The summary should include:
                - The name, quantity, and requested date of each product
                - Whether the request is fulfilled by issuing a quote or not
                - Use 'get_financial_report_summary' and attach a short finantial report at the end
                - Do not include any information indentifying the customer
            """
            return self.accounting_agnet.run(task)

        super().__init__(
            tools=[ 
                search_product,
                get_items_without_matched_products,
                check_inventory,
                order_item,
                is_ready_for_quote,
                create_quote,
                generate_summary_report
            ],
            model=model,
            name="orchestrator",
            description="""
            You are the orchestrator of the inventory management and quoting systems.
            You coordinate between inventory, ordering, and quoting agents.
            """,
        )

    def process_quote_request(self, quote_request: str) -> str:
        """
        Process a quote request
        
        Args:
            quote_request (str): Original quote request
            
        Returns:
            str: Natural language response with quote details
        """
        try:
            context = f""" 
            Quote Request: {quote_request}

            Process the above quote request and generate a response to the customer. Follow the procedure below step by step.:
            Step 1. From the request, identify the products, quantities, and dates needed and requested. Then, use 'search_product' with the identified product names, quantities, and dates needed to store the mapping from the *item name* to the *matching product name* in inventory.
            Step 2. Determine there are any items without the matching products in inventory by using 'get_items_without_matched_products' with the *item names*, quantities, and date needed.
                - If there are any, proceed to Step 5.
                - If not, proceed to Step 3.
            Step 3. Use 'check_inventory' to check the availability by passing the *item names*, quantities, dates needed.
                - If a product is available in inventory, flag it as STOCKED.
                - If not, use 'order_item' with the *item names* to restock. If it can be restocked, flag the product as STOCKED. Otherwise, flag the product as OUT_OF_STOCK
            Step 4. Use 'is_ready_for_quote' with the list of STOCKED/OUT_OF_STOCK flags collected in Step 3.
                - If yes, create a quote by using 'create_quote' with the original request and date of request.
                - If no, proceed to Step 5.
            Step 5. Generate a succinct response to the customer. Always use a professional and friendly tone in the response for a customer.
                - If a quote has been created, respond based on the detailed explanation included in the quote.
                - If a quote couldn't be created, respond with the reason why the request could not be fulfilled.
            Step 6. Generate a summary report by using 'generate_summary_report' with the request and quote if created.
            """
            return self.run(context)
        except Exception as e:
            print(f"Error processing quote request: {str(e)}")
            print(traceback.format_exc())
            return """
            Unfortunately we encountered a technical issue while processing your request. Please try again or contact customer service."
            """


# Run your test scenarios by writing them here. Make sure to keep track of them.

def run_test_scenarios():
    
    print("Initializing Database...")
    init_database(db_engine=db_engine)
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    orchestrator = Orchestrator(model=model)

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        response = orchestrator.process_quote_request(request_with_date)

        # Update state
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response,
            }
        )

        time.sleep(1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()
