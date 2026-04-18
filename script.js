let cart = [];
let allProducts = [];

// ===============================
// CHARGER PRODUITS
// ===============================

function loadProducts() {
    return fetch("/api/products")
        .then(res => res.json())
        .then(data => {
            allProducts = data;
        });
}

// ===============================
// CHARGER CATEGORIES
// ===============================

function loadCategories() {
    fetch("/api/categories")
    .then(res => res.json())
    .then(data => {

        let html = "";

        data.forEach(cat => {
            html += `
                <button onclick="filterCategory('${cat[1]}')">
                    ${cat[1]}
                </button>
            `;
        });

        document.getElementById("categories").innerHTML = html;
    });
}

// ===============================
// FILTRER PAR CATEGORIE
// ===============================

function filterCategory(categoryName) {

    let filtered = allProducts.filter(product =>
        product[3].trim().toLowerCase() === categoryName.trim().toLowerCase()
    );

    let html = "";

    if (filtered.length === 0) {
        html = "<p>Aucun produit dans cette catégorie</p>";
    }

    filtered.forEach(product => {

        html += `
            <div style="border:1px solid black; padding:10px; margin:10px;">
                <h3>${product[1]}</h3>
                <img src="${product[4]}" width="120"><br>
                <strong>${product[2]} DA</strong><br><br>

                Taille :
                <select id="size-${product[0]}">
                    <option value="L">L</option>
                    <option value="XL">XL</option>
                    <option value="XXL">XXL</option>
                </select>
                <br><br>

                Quantité :
                <input type="number" id="qty-${product[0]}" value="1" min="1">
                <br><br>

                Commentaire :
                <input type="text" id="comment-${product[0]}" placeholder="Ex: sans oignon">
                <br><br>

                <button onclick="addToCart(${product[0]}, '${product[1]}', ${product[2]})">
                    Ajouter au panier
                </button>
            </div>
        `;
    });

    document.getElementById("products").innerHTML = html;
}

// ===============================
// AJOUTER AU PANIER
// ===============================

function addToCart(id, name, price) {

    let size = document.getElementById(`size-${id}`).value;
    let qty = document.getElementById(`qty-${id}`).value;
    let comment = document.getElementById(`comment-${id}`).value;

    cart.push({
        name,
        price,
        size,
        qty,
        comment
    });

    updateCart();
}

// ===============================
// AFFICHER PANIER
// ===============================

function updateCart() {

    let html = "";

    cart.forEach((item, index) => {
        html += `
            <div>
                ${item.name} (${item.size}) x${item.qty}
                <br>
                Commentaire: ${item.comment}
                <br>
                <button onclick="removeFromCart(${index})">Supprimer</button>
                <hr>
            </div>
        `;
    });

    document.getElementById("cart").innerHTML = html;
}

// ===============================
// SUPPRIMER PANIER
// ===============================

function removeFromCart(index) {
    cart.splice(index, 1);
    updateCart();
}

// ===============================
// ENVOYER COMMANDE
// ===============================

function sendOrder() {

    let tableNumber = document.getElementById("tableNumber").value;

    if (!tableNumber || tableNumber <= 0) {
        alert("Veuillez entrer un numéro de table valide");
        return;
    }

    if (cart.length === 0) {
        alert("Votre panier est vide !");
        return;
    }

    fetch("/api/add_order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            table: tableNumber,
            items: cart
        })
    })
    .then(res => res.json())
    .then(data => {
        alert("Commande envoyée avec succès !");
        cart = [];
        updateCart();
        document.getElementById("tableNumber").value = "";
    });
}

// ===============================
// INITIALISATION
// ===============================

loadProducts().then(() => {
    loadCategories();
});