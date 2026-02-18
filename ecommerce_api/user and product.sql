CREATE DATABASE simple_shop;
USE simple_shop;

CREATE TABLE users (
	user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) UNIQUE,
    password_hash VARCHAR(255)
    );
    
CREATE TABLE products (
	product_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    price DECIMAL (10,2),
    stock INT
    );
    
SHOW TABLES;
DESCRIBE users;
SELECT * FROM users;

DESCRIBE products;
SELECT * FROM products;
