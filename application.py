import os
import sqlite3
import json
import config
import csv
from flask import Flask, request, session, g, redirect, url_for, abort, jsonify, render_template, flash, send_from_directory
from flask_session import Session
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
import requests
from tempfile import mkdtemp
from datetime import datetime
from helpers import findStoresByZip, wmLabsLookup, invLookup, login_required, cleanLinks
from flask_debugtoolbar import DebugToolbarExtension

# create the application instance :)
app = Flask(__name__)
app.config.from_object(__name__)
SECRET_KEY = config.VARS['SECRET_KEY']

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'walle.db'),
    DEBUG_TB_INTERCEPT_REDIRECTS=False,
))

# enable debugger toolbar
app.debug = False
toolbar = DebugToolbarExtension(app)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = './session'
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def init_db():
    """Initializes DB according to schema.sql"""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database from command line"""
    init_db()
    print('Initialized the database.')

def query_db(query, args=(), one=False):
    """Helper function to query DB"""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        db = get_db()
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("sorry.html", message="Please enter your username.")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("sorry.html")

        # Query database for username
        user = query_db("SELECT * FROM users WHERE username = ?",
                        [request.form.get("username")], one=True)
        # Ensure username exists and password is correct
        if not user or not check_password_hash(user["hash"], request.form.get("password")):
            return render_template("sorry.html", message="Username doesn't exist or password incorrect.")

        # Remember which user has logged in
        print(user["uid"])
        session["user_id"] = user["uid"]
        session["username"] = user['username']
        session["level"] = user['level']
        # Redirect user to home page
        flash(f"Logged in as ({session['username']})!")
        print(session['level'])
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # clears session
    session.clear()
    if request.method == "POST" and request.referrer.find(config.VARS['regKey']):
        db = get_db()
        # checks that all info has been entered and passwords match
        if not request.form.get("username"):
            return render_template("sorry.html", message="Please enter a username.")
        elif not request.form.get("password"):
            return render_template("sorry.html", message="Please enter a password.")
        elif request.form.get("password") != request.form.get("confirmation"):
            return render_template("sorry.html", message="Passwords don't match.")
        else:
            # if all fields are valid, generates password hash
            pw_hash = generate_password_hash(request.form.get("password"))
            # inserts new user along with password hash into users table
            try:
                db.execute("INSERT INTO users (username, hash) VALUES(?, ?)",
                                    [request.form.get("username"), pw_hash])
            except sqlite3.IntegrityError:
                # if user already exists, db query will return None
                return render_template("sorry.html", message="Username already taken.")
            else:
                db.commit()
                # if registration successful, store session ID and redirect to index so user is logged in
                user = query_db("SELECT * FROM users WHERE username =?", [request.form.get("username")], one=True)
                session["user_id"] = user['uid']
                session["username"] = user['username']
                flash(f"Registered as ({session['username']})!")
                return redirect("/")
    elif request.args.get('regkey') == config.VARS['regKey']:
        # brings up registration form if no post data
        return render_template("register.html")
    else: return render_template("sorry.html", message="Registration closed.")


@app.route('/')
@login_required
def index():
    """Shows personalized list of items to search for and stores in which to search"""
    db = get_db()
    items = query_db('SELECT sku, name from itemsToSearch WHERE uid=?', [session["user_id"]])
    stores = query_db('SELECT storesToSearch.id as id, city, state, street FROM storesToSearch\
                       INNER JOIN stores on stores.id = storesToSearch.id WHERE storesToSearch.uid=?'\
                        , [session['user_id']])
    return render_template("index.html", items=items, stores=stores)


@app.route('/browseitems', methods=['GET', 'POST'])
@login_required
def browseitems():
    """Shows entire database of items users have searched for, along with some interesting data"""
    db = get_db()
    level = query_db('SELECT level FROM users where uid=?',[session["user_id"]],one=True)['level']
    if request.method=="GET":
        page = request.args.get('page') or 1
        page = int(page)
        sortby = request.args.get('sortby') or 'numsearches'
        category = request.args.get('category')
        numitems = query_db('SELECT count(*) from itemData', one=True)
        if category:
            print(category)
            numitems = query_db('SELECT count(*) from itemData WHERE categoryNode = ?',[category], one=True)
            database = query_db('SELECT sku, itemData.name, thumbnailImage, categoryPath, categoryNode, numsearches, itemData.upc, SUM(qty) as count, MIN(price) as min, salePrice,\
                   B ROUND((100*(1 - MIN(price*1.0)/salePrice*1.0)),1) as bestDrop from itemData LEFT JOIN inventory on inventory.upc = itemData.upc\
                    WHERE categoryNode = ? GROUP BY itemdata.upc ORDER BY numsearches DESC LIMIT ? OFFSET ?',[category, 100,(page-1)*100])
        elif sortby == 'numsearches':
            database = query_db('SELECT sku, itemData.name, thumbnailImage, categoryPath, categoryNode, numsearches, itemData.upc, SUM(qty) as count, MIN(price) as min, salePrice,\
                                ROUND((100*(1 - MIN(price*1.0)/salePrice*1.0)),1) as bestDrop from itemData LEFT JOIN inventory on inventory.upc = itemData.upc\
                                GROUP BY itemdata.upc ORDER BY numsearches DESC LIMIT ? OFFSET ?',[100,(page-1)*100])
        elif sortby == 'bestdrop':
            database = query_db('SELECT sku, itemData.name, thumbnailImage, categoryPath, categoryNode, numsearches, itemData.upc, SUM(qty) as count, MIN(price) as min, salePrice,\
                        ROUND((100*(1 - MIN(price*1.0)/salePrice*1.0)),1) as bestDrop from itemData LEFT JOIN inventory on inventory.upc = itemData.upc\
                        GROUP BY itemdata.upc ORDER BY bestdrop DESC LIMIT ? OFFSET ?',[100,(page-1)*100])
        return render_template("browseitems.html", database=database, page=page, numitems=numitems, sortby=sortby, level=level, category=category)
    else:
        query = request.form.get('itemsearch')
        database = query_db("SELECT sku, itemData.name, thumbnailImage, categoryPath, categoryNode, numsearches, itemData.upc, SUM(qty) as count, MIN(price) as min, salePrice,\
                    ROUND((100*(1 - MIN(price*1.0)/salePrice*1.0)),1) as bestDrop from itemData LEFT JOIN inventory on inventory.upc = itemData.upc\
                    WHERE itemdata.name like '%'||?||'%' GROUP BY itemdata.upc LIMIT 100",[query])
        return render_template("browseitems.html", database=database, query=query, level=level)


@app.route('/browsestores', methods=['GET'])
@login_required
def browsestores():
    """Show all stores and allow user to add to personal list"""
    db = get_db()
    stores = query_db('SELECT id, city, state, street, zip FROM stores')
    return render_template("browsestores.html", stores=stores)


@app.route('/stores', methods=['POST'])
@login_required
def stores():
    """Allows user to add stores to their list via zip code search or by adding from indexed list on 'Browse Stores'"""
    db = get_db()
    stores = []
    # zip code from index page form
    z = request.form.get("z")
    if z:
        stores = findStoresByZip(z)
        for store in stores:
            # adds stores near zip to database of store info if they don't already exist
            db.execute('INSERT OR IGNORE INTO stores (id, distance, street, city, state, zip, coords) values (?, ?, ?, ?, ?, ?, ?)',
                       [store['id'],  store['distance'], store['street'], store['city'], store['state'], store['zip'], store['coordinates']])
            # adds stores near zip to user's list of stores to search
            db.execute('INSERT OR IGNORE INTO storesToSearch (id, uid) values (?, ?)', [store['id'], session["user_id"]])
        db.commit()
    else:
        # if a user is adding a store via the 'browse stores' page, it must be indexed already, therefore just add to user list
        store = request.data.decode()
        db.execute('INSERT OR IGNORE INTO storesToSearch (id, uid) values (?, ?)', [store, session["user_id"]])
        db.commit()
        # allows user to delete stores from their personal list using checkboxes on index page
    if len(request.form) > 1:
        for key in request.form:
            if key != "z" and key != "allStores":
                db.execute('DELETE FROM storesToSearch WHERE id=? AND uid=?', (key, session["user_id"]))
        db.commit()
    return redirect(url_for('index'))


@app.route('/lookup', methods=['POST'])
@login_required
def lookup():
    """Looks up items using Walmart Mobile API via lists on index page or adds them to user list via button on item page"""
    db = get_db()
    skus = []
    # If coming from index page, converts walmart/brickseek links to skus and adds to array of skus
    if request.form.get("skus"):
        skus = cleanLinks(request.form.get("skus").splitlines())
    else:
        # If refreshing inventory from item page, simply use the sku from the request
        skus.append(request.data.decode())
    if skus:
        for sku in skus:
            # Checks to see if sku is indexed in itemData table to avoid unnecessary API calls
            indexed = query_db('SELECT sku, name, upc FROM itemData WHERE sku=?', [sku], one=True)
            if indexed:
                print(f"Found SKU {sku} in DB!")
                # If indexed, just insert item into itemsToSearch table
                db.execute('INSERT or IGNORE INTO itemsToSearch (uid, sku, name, upc) values (?, ?, ?, ?)',
                            [session['user_id'], indexed['sku'], indexed['name'], indexed['upc']])
            else:
                # If not indexed, lookup item Data and add to itemData and itemsToSearch
                item = wmLabsLookup(sku)
                if item:
                    db.execute('INSERT or IGNORE INTO itemData (sku, name, upc, msrp, salePrice, categoryNode, categoryPath, thumbnailImage, numsearches)\
                                values (?, ?, ?, ?, ?, ?, ?, ?, ?)', [item['sku'], item['name'], item['upc'], item['msrp'], item['salePrice'], item['categoryNode'], item['categoryPath'], item['thumbnailImage'], 0])
                    db.execute('INSERT or IGNORE INTO itemsToSearch (uid, sku, name, upc) values (?, ?, ?, ?)',
                                [session["user_id"], item['sku'], item['name'], item['upc']])
    for key in request.form:
        # Allow user to delete items from their list using checkboxes on index page
        if key != "skus":
            db.execute('DELETE FROM itemsToSearch WHERE sku=? AND uid=?', (key, session['user_id']))
    db.commit()
    # sends user back to index page
    return redirect(url_for('index'))


@app.route('/search', methods=['POST'])
@login_required
def search():
    """Looks up real-time inventory and price data from Walmart Mobile API"""
    db = get_db()
    results = []
    currentStore = {}
    # If looking up a single SKU from the item page, simply find one UPC from db
    if request.args.get('sku'):
        upcs = db.execute('SELECT upc FROM itemData where sku=?', [request.args.get('sku')])
    else:
        # convert a list of SKUs on itemsToSearch to UPCS
        upcs = db.execute('SELECT itemData.upc FROM itemData INNER JOIN itemsToSearch on itemsToSearch.sku = itemData.sku where uid=?',[session["user_id"]])
    # gets list of stores from user's personal list
    stores = db.execute('SELECT id FROM storesToSearch where uid=? AND id > 1', [session["user_id"]])
    storeStr = ""
    # formats string of stores to pass to Walmart API
    for store in stores:
        storeStr += str(store['id']) + ","
    # removes trailing comma
    storeStr = storeStr[:-2]
    # calls invLookup helper to lookup each UPC at string of stores
    for upc in upcs:
        db.execute('UPDATE itemData SET numsearches = numsearches + 1 WHERE upc=?',[upc['upc']])
        results.append(invLookup(upc['upc'], storeStr))
    # iterates through list of results which contain entries for each store
    for result in results:
        try:
            # adds each store inventory / price entry to inventory table
            for store in result['data']:
                try:
                    old_price = query_db('SELECT price FROM inventory WHERE store = ? and upc=?',[store['storeId'],result['origUpc']],one=True)
                    if old_price:
                        if store['packagePrice'] < old_price['price']:
                            db.execute('INSERT INTO priceDrops (store_id, upc, old_price, new_price, qty, datetime)\
                                        values (?, ?, ?, ?, ?, ?)', [int(store['storeId']), result['origUpc'], old_price['price'], store['packagePrice'], store['availabilityInStore'], str(datetime.now())])
                    db.execute('INSERT or REPLACE INTO inventory (upc, store, qty, price, name, datetime)\
                    values (?, ?, ?, ?, ?, ?)', [result['origUpc'], store['storeId'], store['availabilityInStore'], store['packagePrice'], store['name'], str(datetime.now())])
                # passes up if no results
                except KeyError:
                    pass
        except KeyError:
            pass
    db.commit()
    # collects newly acquired data to present to user as results page
    inv = query_db('SELECT inventory.upc as upc, itemData.sku, store, street, city, state, qty, price, datetime, msrp, thumbnailImage, itemData.name, salePrice, ROUND(100.0*(1.0-((1.0*inventory.price)/(1.0*itemdata.salePrice))),2) as discount FROM inventory \
            INNER JOIN itemData ON itemData.upc = inventory.upc INNER JOIN stores ON inventory.store = stores.id INNER JOIN itemsToSearch on itemData.sku=itemstoSearch.sku INNER JOIN storesToSearch on stores.id = storesToSearch.id WHERE qty > 0 AND itemsToSearch.uid = ? and storesToSearch.uid = ? ORDER BY upc', [session["user_id"], session["user_id"]])
    # if looking up a single sku from item page, redirect to the page we came from with updated data
    if request.args.get('sku'):
        return redirect(request.referrer)
    else:
        # otherwise, present a page of all the results
        return render_template("results.html", inv=inv)


@app.route('/update', methods=['POST'])
@login_required
def update():
    """Updates inventory data passed via jQuery"""
    # gets item and store from jquery request
    toUpdate = json.loads(request.data)
    print(toUpdate)
    # looks up item

    db = get_db()
    # updates inventory database with new info
    try:
        result = invLookup(toUpdate['upc'],toUpdate['store'])['data'][0]
        db.execute('INSERT or REPLACE INTO inventory (upc, store, qty, price, name, datetime)\
        values (?, ?, ?, ?, ?, ?)', [toUpdate['upc'], toUpdate['store'], result['availabilityInStore'], result['packagePrice'], result['name'], str(datetime.now())])
    except KeyError:
        db.execute('DELETE FROM inventory WHERE upc=? AND store =?',[toUpdate['upc'],toUpdate['store']])
        db.commit()
        return "Deleted"
    db.commit()
    # packages updated data
    updated = {
        'qty': result['availabilityInStore'],
        'price': result['packagePrice'],
        'timestamp': str(datetime.now())
    }
    # returns data to javascript to be updated asynchronously
    return json.dumps(updated)


@app.route('/item', methods=['GET'])
@login_required
def item():
    """Displays page of specific item's inventory in user's stores or all stores"""
    # gets sku and display all boolean from url
    sku = request.args.get("sku")
    everything = request.args.get("everything")
    db = get_db()
    level = query_db('SELECT level FROM users where uid=?',[session["user_id"]],one=True)['level']
    # only displays items that are in stock and on user's list
    if not everything:
        inv = query_db('SELECT inventory.upc as upc, itemData.sku as sku, store, street, city, state, qty, price, datetime, msrp, salePrice, thumbnailImage, itemData.name FROM inventory \
                INNER JOIN itemData ON itemData.upc = inventory.upc INNER JOIN stores ON inventory.store = stores.id INNER JOIN storesToSearch on inventory.store = storesToSearch.id WHERE qty > 0 AND itemData.sku = ? AND storesToSearch.uid=? ORDER BY store',
                       [sku, session['user_id']])
    else:
        # displays inventory in all stores, even out of stock
        inv = query_db('SELECT inventory.upc as upc, itemData.sku as sku, store, street, city, state, qty, price, datetime, msrp, salePrice, thumbnailImage, itemData.name FROM inventory \
                        INNER JOIN itemData ON itemData.upc = inventory.upc INNER JOIN stores ON inventory.store = stores.id  AND itemData.sku = ?  GROUP BY  store', [sku])
    if not inv:
        return render_template("sorry.html", everythingUrl = "/item?sku="+sku+"&everything=True", message = "No inventory for this item at your stores.")
    return render_template("item.html", inv=inv, everything=everything, level=level)


@app.route('/store', methods=['GET'])
@login_required
def store():
    """Displays all in stock items associated with a certain store"""
    store = request.args.get("store")
    db = get_db()
    inv = query_db('SELECT inventory.upc as upc, categoryPath, sku, store, street, city, state, qty, price, datetime, salePrice,\
                    ROUND((100*(1 - (price*1.0)/salePrice*1.0)),1) as droppy, thumbnailImage, itemData.name FROM inventory \
                    INNER JOIN itemData ON itemData.upc = inventory.upc INNER JOIN stores ON inventory.store = stores.id WHERE qty > 0 AND store = ? ORDER BY sku', [store])
    if not inv:
        return render_template("sorry.html", message="No stock found at this store.")
    else:
        return render_template("store.html", inv=inv)

@app.route('/deals', methods=['GET'])
@login_required
def deals():
    db = get_db()
    discount = request.args.get("discount") or 75.0
    discount = float(discount)
    groupbystores = request.args.get("groupbystores")
    q = 'SELECT *, itemdata.name as realname, ROUND(100.0*(1.0-((1.0*inventory.price)/(1.0*itemdata.salePrice))),2) as discount\
    from inventory INNER JOIN itemData on inventory.upc = itemData.upc INNER JOIN storestosearch ON inventory.store = storestosearch.id\
    INNER JOIN stores on stores.id = storestosearch.id WHERE discount>? AND saleprice > 0 AND QTY > 0 AND uid=? ORDER BY itemdata.name'
    deals = query_db(q,[discount,session["user_id"]])
    return render_template('deals.html', deals=deals)

@app.route('/pricedrops', methods=['GET'])
@login_required
def pricedrops():
    db = get_db()
    yourdrops = []
    upcs = query_db('SELECT DISTINCT upc from priceDrops ORDER BY datetime DESC LIMIT 100')
    print(upcs)
    for upc in upcs:
        upc = upc['upc']
        yourdrops.append(query_db('SELECT * from priceDrops inner join itemdata on pricedrops.upc = itemdata.upc inner join stores on pricedrops.store_id = stores.id where itemdata.upc = ? ORDER BY datetime DESC',[upc]))
    print(yourdrops)
    return render_template('pricedrops.html', upcs = upcs, yourdrops=yourdrops)
        
@app.route('/admin', methods=['GET'])
@login_required
def admin():
    """Admin page"""
    db= get_db()
    level = query_db('SELECT level FROM users where uid=?',[session["user_id"]],one=True)['level']
    if level > 1:
        return render_template("admin.html")
    else: 
        return render_template("sorry.html", message="You're no administrator!")


@app.route('/admin/items', methods=['GET'])
@login_required
def adminitems():
    """Admin Item page"""
    db= get_db()
    level = query_db('SELECT level FROM users where uid=?',[session["user_id"]],one=True)['level']
    if level > 1:
        items = query_db('SELECT * from Itemdata')
        return render_template("adminitems.html", items=items)
    else: 
        return render_template("sorry.html", message="You're no administrator!")

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def users():
    """Admin User page"""
    db= get_db()
    level = query_db('SELECT level FROM users where uid=?',[session["user_id"]],one=True)['level']
    #if an admin is logged in
    if level > 1:
            if request.method=="GET":
                #if a user is specified
                if request.args.get("user"):
                    user = query_db('SELECT * FROM users where username=?',[request.args.get("user")])
                    if user:
                        return render_template("user.html", user=user)
                    else:
                        return render_template("sorry.html", message="User not found!")
                else:
                    users = query_db('SELECT * FROM users')
                    return render_template("users.html", users=users)
            elif request.method=="POST":
                uid = request.form.get("uid")
                if request.form.get("confirm") == "Delete":
                    db.execute('DELETE FROM users WHERE uid=?',[uid])
                    db.execute('DELETE FROM itemsToSearch WHERE uid=?',[uid])
                    db.execute('DELETE FROM storesToSearch WHERE uid=?',[uid])
                    db.commit()
                    flash(f"Deleted User #{uid}!")
                    return redirect("/admin/users")
                elif request.form.get("updateUser") == "Update":
                    username = request.form.get("username")
                    email = request.form.get("email")
                    try:
                        level = int(request.form.get("level"))
                    except ValueError:
                        return render_template("sorry.html", message="Invalid level")
                    print(level)
                    if level == 1 or level == 2:
                        try: 
                            db.execute('UPDATE users SET username = ?, email = ?, level = ? WHERE uid=?',[username, email, level, uid])
                            db.commit()
                            return redirect("/admin/users")
                        except sqlite3.IntegrityError:
                            return render_template("sorry.html", message="Username already exists")
                    else: 
                        return render_template("sorry.html", message="Invalid level")
                elif request.form.get("resetPass") == "Reset":
                    TEMP_PW="ChangeMe123!"
                    tempHash = generate_password_hash(TEMP_PW)
                    db.execute('UPDATE users SET hash = ? where uid=?',[tempHash,uid])
                    db.commit()
                    return redirect("/admin/users")
    else: 
        return render_template("sorry.html", message="You're no administrator!")

@app.route('/adminedit', methods=['POST'])
@login_required
def adminedit():
    db= get_db()
    level = query_db('SELECT level FROM users where uid=?',[session["user_id"]],one=True)['level']
    if level > 1:
        key = request.form.get('name')
        sku = request.form.get('pk')
        value = float(request.form.get('value'))
        if key=="salePrice":
            db.execute('UPDATE itemData SET salePrice = ? WHERE sku = ?', [value, sku])
            db.commit()
            return "DB UPDATED!"
    else:
        return "YOU NO ADMIN"

@app.route('/delete', methods=['POST'])
@login_required
def delete():
    """Allows admin to delete items from main DB."""
    db = get_db()
    level = query_db('SELECT level FROM users where uid=?',[session["user_id"]],one=True)['level']
    if level > 1:
        sku = json.loads(request.data);
        upc = query_db('SELECT upc FROM itemData WHERE sku=?',[sku])[0]['upc']
        db.execute('DELETE FROM itemData WHERE sku=?',[sku])
        db.execute('DELETE FROM itemsToSearch WHERE sku=?',[sku])
        if upc:
                db.execute('DELETE FROM inventory WHERE upc=?',(upc,))
                db.execute('DELETE FROM priceDrops WHERE upc=?',(upc,))
        db.commit()
        return "ITEM DELETED!"

@app.route('/reports')
@login_required
def reports():
    """Generate reports on various data"""
    db = get_db()
    level = query_db('SELECT level FROM users where uid=?',[session["user_id"]],one=True)['level']
    report =  request.args.get('report')
    if level > 1:
        if report:
                if report=="itemdata":
                    with open('reports/itemdata.csv', 'w') as f:
                        writer = csv.writer(f)
                        headers = query_db("PRAGMA table_info(itemdata)")
                        rows = query_db('select * FROM itemdata')
                        writer.writerow([header[1] for header in headers])
                        for row in rows:
                            writer.writerow([item for item in row])
                    return send_from_directory('reports', 'itemdata.csv', as_attachment=True)
                elif report=="inventory":
                    with open('reports/inventory.csv', 'w') as f:
                        writer = csv.writer(f)
                        headers = query_db("PRAGMA table_info(inventory)")
                        rows = query_db('select * FROM inventory')
                        writer.writerow([header[1] for header in headers])
                        for row in rows:
                            writer.writerow([item for item in row])
                    return send_from_directory('reports', 'inventory.csv', as_attachment=True)
                elif report=="pricedrops":
                    with open('reports/pricedrops.csv', 'w') as f:
                        writer = csv.writer(f)
                        headers = query_db("PRAGMA table_info(pricedrops)")
                        rows = query_db('select * FROM pricedrops')
                        writer.writerow([header[1] for header in headers])
                        for row in rows:
                            writer.writerow([item for item in row])
                    return send_from_directory('reports', 'pricedrops.csv', as_attachment=True)        
        else:
            return render_template("reports.html")
    else:
        return render_template("sorry.html", message="Reports for admins only.")

@app.route('/shoppinglist', methods=['GET', 'POST'])
@login_required
def shoppinglist():
    db = get_db()
    if request.method=="GET":
        yourlist = query_db('SELECT * from shoppingList\
                    INNER JOIN inventory on shoppinglist.upc=inventory.upc and shoppinglist.store=inventory.store\
                    INNER JOIN itemdata on itemdata.upc=shoppinglist.upc\
                    INNER JOIN stores on stores.id=shoppinglist.store\
                    WHERE uid=?',[session["user_id"]])
        return render_template('shoppinglist.html',yourlist=yourlist)
    elif request.method=="POST":
        if request.form.get("delete"):
            db.execute("DELETE FROM shoppinglist WHERE uid=? and upc=? and store=?",[session["user_id"],request.form.get("upc"),request.form.get("store")])
            print("DELETE!!")
            db.commit()
            return "1"
        else:
            db.execute('INSERT OR IGNORE INTO shoppinglist (uid, upc, store) VALUES(?, ?, ?)',[session["user_id"],request.form.get("upc"),request.form.get("store")])
            db.commit()
            return "0"

@app.route('/help', methods=['GET'])
@login_required
def help():
    return render_template("help.html")

if __name__ == "__main__":
    app.run(host = '0.0.0.0', port=80)

app.run(host = '0.0.0.0', port=8080, debug=True)