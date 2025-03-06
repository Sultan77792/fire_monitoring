CREATE DATABASE forest_fires_db;
USE forest_fires_db;

CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('operator', 'engineer', 'analyst', 'admin') NOT NULL,
    region VARCHAR(100),
    INDEX idx_username (username)
);

CREATE TABLE kgu_oopt (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE fires (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fire_date DATE NOT NULL,
    region VARCHAR(100) NOT NULL,
    kgu_oopt_id INT,
    area DECIMAL(10, 2) NOT NULL,
    forces_involved TEXT,
    damage DECIMAL(15, 2),
    file_path VARCHAR(255),
    file_name VARCHAR(255),
    created_by INT,
    FOREIGN KEY (created_by) REFERENCES user(id),
    FOREIGN KEY (kgu_oopt_id) REFERENCES kgu_oopt(id),
    INDEX idx_region_date (region, fire_date)
);

CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INT,
    action VARCHAR(50),
    table_name VARCHAR(50),
    record_id INT,
    changes TEXT,
    FOREIGN KEY (user_id) REFERENCES user(id),
    INDEX idx_user_time (user_id, log_time)
);

INSERT INTO user (username, password, role, region) VALUES 
('admin1', 'Qaz12345', 'admin', NULL),
('operator1', 'operatorAkm', 'operator', 'Akmola'),
('engineer1', 'eng1', 'engineer', 'Akmola'),
('analyst', 'qaz123', 'analyst', NULL);

INSERT INTO kgu_oopt (name) VALUES 
('Национальный парк "Бурабай"'),
('Государственный лесной фонд Актобе'),
('Заповедник "Алтын-Эмель"');