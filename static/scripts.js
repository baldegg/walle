/* global $*/



$(document).ready(function() {
  $("#allitems").tablesorter();
  $("#allstores").tablesorter();
  $("#iteminv").tablesorter();
  $("#storestock").tablesorter();
  $("#users").tablesorter();
  $("#adminitems").tablesorter();


  $('.masterCheck').click(function() {
    $(this).closest('table').find('.slaveCheck').each(function() {
      $(this).click();
    });
  });
  
});

function loading() {
  console.log("loading");
  $(".progress").show();
  $(".content").hide();
}


function updateInv() {
  var store = $(document.activeElement).parent().next()[0].innerText;
  var upc = $("#upc")[0].innerText;
  var data = {
    "store": store,
    "upc": upc
  }
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      var updated = JSON.parse(this.responseText);
      $(document.activeElement).parent().parent().children()[5].innerText = updated['qty'];
      $(document.activeElement).parent().parent().children()[6].innerText = "$" + updated['price'];
      $(document.activeElement).parent().parent().children()[7].innerText = updated['timestamp'];
    }
  };
  xhttp.open("POST", "/update", true);
  xhttp.send(JSON.stringify(data));
}

function updateStore() {
  var upc = $(document.activeElement).parent().parent().children()[4].innerText;
  var store = $('#store')[0].innerText;
  var data = {
    "store": store,
    "upc": upc
  }
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      console.log(this.responseText);
      var updated = JSON.parse(this.responseText);
      $(document.activeElement).parent().parent().children()[5].innerText = updated['qty'];
      $(document.activeElement).parent().parent().children()[6].innerText = "$" + updated['price'];
      $(document.activeElement).parent().parent().children()[10].innerText = updated['timestamp'];
    }
  };
  xhttp.open("POST", "/update", true);
  xhttp.send(JSON.stringify(data));
}

function addItem() {
  var sku = $(document.activeElement)[0]['id'].replace('.add', '');
  console.log(sku);
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      $(document.activeElement)[0].innerText = "ADDED!"
    }
  };
  xhttp.open("POST", "/lookup", true);
  xhttp.send(sku);
}

function addStore() {
  var store = $(document.activeElement)[0]['id'].replace('.add', '');
  console.log(store);
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      $(document.activeElement)[0].innerText = "ADDED!"
    }
  };
  xhttp.open("POST", "/stores", true);
  xhttp.send(store);
}

function loadStores() {
  loading();
  var sku = $(document.activeElement)[0]['id'].replace('.add', '');
}

function confirmDelete() {
  $(".confirm").show();
}

function showEdit() {
  $(".edit").show();
}