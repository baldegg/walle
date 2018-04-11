import requests
from functools import wraps
from flask import redirect, session
import re
import os
import config

apiKey =  config.VARS['wmLabsApiKey']
searchUrl =  config.VARS['searchUrl']


# pretend to be a droid
headers = {
    "User-Agent": "Android v17.22.4",
    "Host": "search.mobile.walmart.com",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
}


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def findStoresByZip(z):
    """Returns list of stores within ~50 miles of specified zip"""
    store = {}
    stores = []
    print(z)
    url = f'https://www.walmart.com/store/ajax/detail-navigation?location={z}'
    r = requests.get(url).json()
    if 'payload' in r:
        for currentStore in r['payload']['stores']:
            store['id'] = currentStore['id']
            store['distance'] = currentStore['distance']
            store['street'] = currentStore['address']['address1']
            store['city'] = currentStore['address']['city']
            store['state'] = currentStore['address']['state']
            store['zip'] = currentStore['address']['postalCode']
            store['coordinates'] = currentStore['geoPoint']['coordString']
            stores.append(store)
            store = {}
    return stores


def wmLabsLookup(sku):
    """Gets info about an item using Walmart Labs API"""
    print(sku)
    url = f"http://api.walmartlabs.com/v1/items/{sku}?format=json&apikey={apiKey}"
    r = requests.get(url).json()
    if r:
        if not 'errors' in r:
            item = {
                "sku": r['itemId'],
                "name": r['name'],
                "upc": r['upc'],
                "msrp": r['msrp'] if 'mrsp' in r else "-1",
                "salePrice": r['salePrice'] if 'salePrice' in r else "-1",
                "categoryNode": r['categoryNode'],
                "categoryPath": r['categoryPath'],
                "thumbnailImage": r['thumbnailImage']
            }
        else:
            item = None
    else:
        item = None
    return item


def invLookup(upc, stores):
    """Uses Walmart Mobile API to lookup real time inventory/price info"""
    origUpc = upc
    upc = fixUpc(upc)
    print(upc)
    url = f"{searchUrl}={stores}&barcodes={upc}"
    print(url)
    r = requests.get(url, headers=headers).json()
    r['origUpc'] = origUpc
    print(r)
    return r


def fixUpc(upc):
    """Converts UPC to format suitable for Walmart Mobile API"""
    upc = str(upc)[:-1]
    if len(upc) == 10:
        upc = "WUPC.000" + upc
    else:
        upc = "WUPC.00" + upc
    return upc


def cleanLinks(urls):
    """Sanitizes input and extracts SKU from Walmart and Brickseek links using RegEx"""
    r = '(\d\d\d\d\d\d\d\d\d)|(\d\d\d\d\d\d\d\d)|(\d\d\d\d\d\d\d)'
    skus = []
    for url in urls:
        m = re.search(r, url)
        if m:
            skus.append(m.group(0))
    return skus


# DEPRECATED FUNCTIONS---------------------------------------------------------------------------
# def findItemsByZip(sku, z):
#     """Terra Firma API - Deprecated"""
#     results = []
#     url = f'https://www.walmart.com/terra-firma/item/{sku}/location/{z}?selected=true&wl13='
#     r = requests.get(url, headers=headers).json()
#     for offer in r['payload']['offers']:
#         if r['payload']['offers'][offer]['offerInfo']['offerType'] == "ONLINE_AND_STORE":
#             results = r['payload']['offers'][offer]['fulfillment']['pickupOptions']
#     return results

# def findItemsByStore(skus, stores):
#     """Mobile Search API - Deprecated"""
#     returnItems = []
#     for sku in skus:
#         for store in stores:
#             url = f'https://search.mobile.walmart.com/search?query={sku}&store={store}'
#             r = requests.get(url, headers=headers).json()
#             try:
#                 returnItem = {}
#                 itemData = r['results'][0]
#                 returnItem['store'] = store
#                 returnItem['sku'] = sku
#                 try:
#                     returnItem['name'] = itemData['name']
#                 except KeyError:
#                     returnItem['name'] = "No data."
#                 try:
#                     returnItem['img'] = itemData['images']['thumbnailUrl']
#                 except KeyError:
#                     returnItem['img'] = "No data."
#                 try:
#                     returnItem['price'] = itemData['price']['priceInCents']
#                 except KeyError:
#                     returnItem['price'] = "No data."
#                 try:
#                     returnItem['qty'] = itemData['inventory']['quantity']
#                 except KeyError:
#                     returnItem['qty'] = "No data."
#                 try:
#                     returnItem['upc'] = itemData['productId']['upc']
#                 except KeyError:
#                     returnItem['upc'] = "No data."
#                 returnItems.append(returnItem)
#             except IndexError:
#                 print(f'item {sku} not found at store {store}')
#             except KeyError:
#                 print(f'item {sku} not found at store {store}!!')
#     return returnItems
