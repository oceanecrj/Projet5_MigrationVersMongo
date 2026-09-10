// Utilisateur admin
db.createUser({
    user: "admin_mongo",
    pwd: "Admin2026OPC.",
    roles: [
        {role: "dbOwner", db: "Healthcare"}
    ]
});

// Utilisateur lecture / écriture non admin
db.createUser({
    user: "Gestionnaire",
    pwd: "Gestionnaire2026OPC.",
    roles: [
        {role: "readWrite", db: "Healthcare"}
    ]
});

// Utilisateur lecture seule
db.createUser({
    user: "Soignant",
    pwd: "Soignant2026OPC.",
    roles: [
        {role: "read", db: "Healthcare"}
    ]
});