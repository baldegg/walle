drop table if exists stores;
drop table if exists inventory;
drop table if exists itemData;
drop table if exists storesToSearch;
drop table if exists itemsToSearch;
drop table if exists users;

create table stores (
  id integer primary key not null,
  street text not null,
  distance numeric not null,
  city text not null,
  state text not null,
  zip integer not null,
  coords numeric not null
);

create table storesToSearch(
  id integer not null,
  uid integer not null,
  PRIMARY KEY (id, uid)
);
create table itemsToSearch(
  uid numeric not null,
  sku numeric not null,
  checked integer,
  name text,
  upc numeric,
  PRIMARY KEY (sku, uid)
);

create table itemData(
  sku numeric not null primary key,
  name text,
  upc numeric,
  msrp numeric,
  salePrice numeric,
  categoryNode text,
  categoryPath text,
  thumbnailImage text,
  added timestamp,
  numsearches integer
);

create table priceDrops(
drop_id numeric primary key autoincrement,
upc numeric not null,
store_id numeric not null,
old_price numeric not null,
new_price numeric not null,
qty numeric not null,
datetime timestamp not null
);

create table inventory (
  upc numeric not null,
  store integer not null,
  qty numeric,
  price numeric,
  name text,
  datetime timestamp,
  PRIMARY KEY (upc, store)
);

create table users (
  uid integer primary key autoincrement,
  username text unique not null,
  hash text not null,
  email text
  level integer not null
);