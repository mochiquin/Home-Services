-- Database initialization script
-- Create database and user (if not exists)

CREATE DATABASE IF NOT EXISTS homeservices CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (if not exists)
CREATE USER IF NOT EXISTS 'homeservices'@'%' IDENTIFIED BY 'homeservices123';

-- Grant privileges
GRANT ALL PRIVILEGES ON homeservices.* TO 'homeservices'@'%';

-- Flush privileges
FLUSH PRIVILEGES;

-- Use database
USE homeservices;

-- Set character set
SET NAMES utf8mb4;

