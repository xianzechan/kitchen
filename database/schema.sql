CREATE DATABASE IF NOT EXISTS cake_inventory;
USE cake_inventory;

-- Users table
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'warehouse', 'kitchen', 'operations') NOT NULL
);

-- Raw Ingredients
CREATE TABLE raw_ingredients (
    ingredient_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    quantity DECIMAL(10,2) DEFAULT 0,
    unit VARCHAR(10) DEFAULT 'g',
    cost_per_unit DECIMAL(10,2) NOT NULL,
    expiry_date DATE,
    threshold INT DEFAULT 2
);

-- Semi-finished Products
CREATE TABLE semi_finished (
    semi_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    quantity INT DEFAULT 0,
    expiry_date DATE,
    threshold INT DEFAULT 2
);

-- Final Products
CREATE TABLE final_products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    quantity INT DEFAULT 0
);

-- Recipe for Semi-finished Products
CREATE TABLE semi_finished_recipe (
    recipe_id INT PRIMARY KEY AUTO_INCREMENT,
    semi_id INT,
    ingredient_id INT,
    quantity_needed DECIMAL(10,2) NOT NULL,
    output_quantity INT NOT NULL,
    FOREIGN KEY (semi_id) REFERENCES semi_finished(semi_id),
    FOREIGN KEY (ingredient_id) REFERENCES raw_ingredients(ingredient_id)
);

-- Recipe for Final Products
CREATE TABLE final_product_recipe (
    recipe_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT,
    semi_id INT,
    quantity_needed INT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES final_products(product_id),
    FOREIGN KEY (semi_id) REFERENCES semi_finished(semi_id)
);

-- Wastage Tracking
CREATE TABLE wastage (
    wastage_id INT PRIMARY KEY AUTO_INCREMENT,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    item_type ENUM('raw', 'semi', 'final') NOT NULL,
    item_id INT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    reason TEXT NOT NULL,
    recorded_by INT,
    FOREIGN KEY (recorded_by) REFERENCES users(user_id)
);
