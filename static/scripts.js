/* global $*/

$(document).ready(function() {
  //make tables sortable
  $('.tablesorter').tablesorter();
    $('.modal').modal();
  //enables check/uncheck all boxes 
  $('.masterCheck').click(function() {
    $(this).closest('table').find('.slaveCheck').each(function() {
      $(this).click();
    });
  });

});

//show loading bar
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
      console.log(updated);
      $(document.activeElement)[0].innerHTML = "<i class='refresh material-icons'>sync_problem</i>"
      $(document.activeElement).parent().siblings("#qty")[0].innerText = updated['qty'];
      $(document.activeElement).parent().siblings('#price')[0].innerText = "$" + updated['price'];
      $(document.activeElement).parent().siblings("#timestamp")[0].innerText = updated['timestamp'];
    }
  };
  xhttp.open("POST", "/update", true);
  xhttp.send(JSON.stringify(data));
}

function updateShoppingListInv(upc, store) {
  var data = {
    "store": store,
    "upc": upc
  }
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      if (this.responseText !="Deleted"){
      var updated = JSON.parse(this.responseText);
      $(document.activeElement).parent().siblings("#qty")[0].innerText = updated['qty'];
      $(document.activeElement).parent().siblings("#price")[0].innerText = "$" + updated['price'];
      $(document.activeElement).parent().siblings("#timestamp")[0].innerText = updated['timestamp'];
      }
      else{
        console.log("poop")
      $(document.activeElement).siblings("#qty")[0].innerText('0'); 
      $(document.activeElement).parentElement.css('color', 'red'); 
      }
    }
  };
  xhttp.open("POST", "/update", true);
  xhttp.send(JSON.stringify(data));
}



function updateStore(upc) {
  var upc = upc
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
      $(document.activeElement).parent().siblings("#qty")[0].innerText = updated['qty'];
      $(document.activeElement).parent().siblings('#price')[0].innerText = "$" + updated['price'];
      $(document.activeElement).parent().siblings("#timestamp")[0].innerText = updated['timestamp'];
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
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      $(document.activeElement)[0].innerText = "ADDED!"
    }
  };
  xhttp.open("POST", "/stores", true);
  xhttp.send(store);
}

function addToShoppingList(upc, store) {
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      $(document.activeElement)[0].innerHTML = "<i class='material-icons'>playlist_add_check</i>"

    }
  };
  xhttp.open("POST", "/shoppinglist", true);
  xhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
  xhttp.send("upc=" + upc + "&store=" + store);
}

function deleteFromShoppingList(upc, store) {
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      $(document.activeElement).closest('tr').css("display", "none");
    }
  };
  xhttp.open("POST", "/shoppinglist", true);
  xhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
  xhttp.send("upc=" + upc + "&store=" + store + "&delete=true");
}


function loadStores() {
  loading();
  var sku = $(document.activeElement)[0]['id'].replace('.add', '');
}


function confirmDelete() {
  $(document.activeElement).next('button').toggle();
}

function showEdit() {
  $(".edit").show();
}

function adminDelete(sku) {
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      $(document.activeElement).text("DELETED!");
      $(document.activeElement).closest('tr').css("display", "none");
    }
  };
  xhttp.open("POST", "/delete");
  xhttp.send(sku);
}

function showItems() {
  $('.tables').hide()
  $('.items').show()
}

function showTables() {
  $('.items').hide()
  $('.tables').show()
}
