# Multi-Agent Inventory Management / Quoting System

In response to a quote request, this multi-agent system checks inventory status, provides a quote, and record transactions.

## Architecture

### Workflow

1. Upon receipt of request, **Orchestrator** identifies the products, quantities, and delivery dates from a quote request.
2. **Inventory manager** finds the matching products available in inventory. The mapping between the product names in the request and those matched in inventory is stroed in a short-term memory for later use.
    - The attached diagram shows how this short-term-memory is written and read by the dashed arrows.
3. For each product, determine if it can be fullfilled by following the steps below:
    - **Inventory Agent** checks the product's availability on the requested date.
        - If yes, flag as *STOCKED*.
    - Otherwise, **Ordering Agent** attempts to restock the product.
        - If yes, flag as *STOCKED*.
        - If no, flag as *OUT_OF_STOCK*.
4. **Orchestrator** check if all the products are flagged as *STOCKED*.
    - If yes, **Quoteing Agent** generates a quote.
5. **Orchestrator** responds to the customer with a quote or the reasons why the request cannot be fulfilled.
6. **Accounting Agent** generates a summary report.

### Agents and Roles

1. Orchestrator
    - Coordinates bewteen inventory, ordering, quoting, and accounting agents.
        - Teams up with the inventory and ordering agents to ensure that products are in stock.
        - Responds to customer inquiries by providing quotes prepared by the quoting agent or explanations why the request cannot be fulfilled.
        - Forwards to the accounting agent for a summary report.
    - Available tools: `search_product`, `get_items_without_matched_products`, `check_inventory`, `order_item`, `is_ready_for_quote`, `create_quote`, `generate_summary_report`
        - The attached diagram shows how these tools are used in sequence based on the tools' responses. Please follow the thick arrows within the box representing the Orchestator agent.

2. Inventory Agent
    - Responsible for storage and tracking
    - Available tools: `find_matching_product_in_inventory`, `is_available_in_inventory`
        - As shown in the workflow diagram, these tools retrieve necessary information from database.
        
3. Ordering Agent
    - Responsible for restocking
    - Available tools: `can_be_restocked`, `submit_order`   
        - As shown in the workflow diagram, the `submit_order` tool creates records in database, and the `can_be_restocked` tool consults suppliers.

4. Quoting Agent
    - Responsible for issuing quotes
    - Available tools: `get_unit_price`, `find_historical_quotes_with_discount`, `submit_sale`
        - As shown in the workflow diagram, the `find_historical_quotes_with_discount` and `get_unit_price` tools retrieve necessary information from database, and the `submit_sale` tool creates records in database.
       
5. Accounting Agent
    - Responsible for reporting.
    - Available tools: `generate_financial_summary`
        - As shown in the workflow diagram, the `generate_financial_summary` tool retrieve necessary information from database.

### Why this architecture?
The motivation for the chosen architecure is to issue a quote **only** when all the items in a given request can be fulfilled. In order to achieve the goal, the orchestrator needs to determine if all the item are in the list of products provided by the company and if all the items are in stock or can be stocked before the needed date. These taks are delegated to the inventory and ordering agents who are responsible for manageing inventory and restocking items, respectively. When it is possible to issue a quote, the orchestrator delegates the quoting agent to handle tasks such as composing the detailed explanation and creating a transaction record for sale. In the end, the orchestrator hands the request and quote over to the accounting agent for reporting.


## Discussion 

### Summary of processing the requests provided in `quote_requests_sample.csv`
The results of processing the requests provided in `quote_requests_sample.csv` are attached as `test_results.csv` and summarized in the table below. In addition, the whole output is attached as `output.txt`.

| Request # | Quoted/Not Quoted | Cash Balance | Inventory Value | Notes |
| --- | --- | --- | --- | --- |
|  1 | Quoted | 45094.7 | 4905.299999999999 | $35.00, No discount |
|  2 | Not Quoted | 45094.7 | 4905.299999999999 | do not provide with balloons or streamers |
|  3 | Not Quoted | 44294.7 | 5905.299999999999 | A3 paper and printer paper are not provided |
|  4 | Quoted | 44234.9 | 5892.799999999999 | Discount applied $87.50 -> $80.00 |
|  5 | Not Quoted | 44234.9 | 5892.799999999999 | do not provide decorative washi tape |
|  6 | Not Quoted | 44234.9 | 5892.799999999999 | items are not provided |
|  7 | Not Quoted | 44234.9 | 5892.799999999999 | unable to provide Matte A3 paper |
|  8 | Quoted | 44074.9 | 6092.8 | working on restocking |
|  9 | Quoted | 44097.899999999994 | 6072.8 | $35.00, No discount |
| 10 | Quoted | 43866.25 | 6217.8 | $145.00, No discount |
| 11 | Quoted | 43866.5 | 6102.8 | $115.0, No discount |
| 12 | Not Quoted | 44097.899999999994 | 6072.8 | not available for restock |
| 13 | Not Quoted | 44097.899999999994 | 6072.8 | cardstock cannot be restocked |
| 14 | Not Quoted | 43866.5 | 6102.8 | cannot be restocked in time |
| 15 | Not Quoted | 43866.5 | 6102.8 | not provide cardboard |
| 16 | Not Quoted | 43866.5 | 6102.8 | not a product we provide |
| 17 | Not Quoted | 43866.5 | 6102.8 | Cannot be restocked & do not provide |
| 18 | Not Quoted | 43866.5 | 6102.8 | not available & do not provide |
| 19 | Quoted | 43626.95 | 5777.8 | $325, No discount |
| 20 | Not Quoted | 43626.95 | 5777.8 | do not provide |

### Observations
1. The cash balance changed at least 5 times.
2. Seven quote requests are successfully fulfilled.
3. For the unfulfilled requests, the responses contain the phrases like "not provided" and "cannot be restocked".

### Strengths
1. The multi-agent system is able to identify the list of item names, quantities, and dates needed directly from requests provided in natural language
2. The multi-agent system expoits a short-term memory to keep the mapping between product names from quote requests and those provided from the inventory, which makes the agents act on the same products while processing a single request
3. Before issuing a quote, the multi-agent system makes sure that all the items in a request can be fulfilled, including attempting to restock products.
4. When a quote cannot be issued, the multi-agent system generates responses with explanations why requests cannot be fulfilled 

### Areas for improvements
1. The heuristic mapping may be replaced with fuzzy matching [1] or similarity search
2. The cash balance mostly decreased. The ordering agent may still order products for restocking even though it is decided that a request cannot be fulfilled in the end.
3. Finding similar quotes in the past may be improved by using a vector database and similarity search
4. The decision process on discounts may be improved by enhancing the prompt together with additional tools quantifying the order size.

## Futher improvements

1. Use similarity search to map bewteen product names from quote requests and those provided from the inventory
2. Hold stocking orders until issung a quote is confirmed.
3. Store quotes in the past into a vector database, so similarity search can be applied to look for simliar quotes.
4. Add an evaluation agent to proofread and revise responses.

[1] [Fuzzy matching via agent required?](https://knowledge.udacity.com/questions/1081106)