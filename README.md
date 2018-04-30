# Wall E World
## A Flask application for simplifying bulk Walmart inventory/price checking.

### Dependencies

* Python 3.6+
* Flask
* flask-session
* Materialize ( http://materializecss.com/ ) 
* Table Sorter ( http://tablesorter.com )
* Walmart Labs API key

### Basic Usage

1. On the home screen, enter your zip code and press "Update Stores" to populate your list of stores to search.
2. Paste a list of SKUs, Walmart.com links, or Brickseek links in the text area under "Items to Search" and press "Update Items".
3. Once your lists of items and stores are populated, press the orange button at the top of the home page to search for all item at all stores.
4. View the color coded results page. Click the remove_red_eye icon to hide items or the list icon to add the item to your shopping list.

### Features

* Multi-user support
  * Each user can maintain personal lists of stores to search, items to search, and personal shopping lists of inventory to track.
* Bulk searching of items and stores
  * The program has no problem searching lists of 100+ items at 30+ stores.
* Item Browse Page
  * Browse through all indexed items with pagination, search, category filtering, and sorted tables.
  * Add items to your lists asynchronously
* Asynchronous Updating
  * Update realtime inventory/price data via Ajax requests.
* Price drop page
  * Dynamically updated page of all known price drops identified by user searching.
* Conditional formatting
  * Results page and deals page have cells colored based on magnitude of discount for easy identification of deals.
* Admin page
  * Manage users, delete items from database, edit data inline
* CSV Reports
  * Admins may generate CSV reports of indexed items, inventory, and price drops.
  
### To Do
* Migrate from SQLite to a more robust db.
* Make results page better organized and more attractive.
* Implement email notifications and password reset.
* Implement list management and notifications via Telegram.
* Implement user settings page.
* Implement item ignore list.
