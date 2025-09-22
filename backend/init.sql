-- Database initialization script
-- Create database and user (if not exists)

CREATE DATABASE IF NOT EXISTS secuflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (if not exists)
CREATE USER IF NOT EXISTS 'secuflow'@'%' IDENTIFIED BY 'secuflow123';

-- Grant privileges
GRANT ALL PRIVILEGES ON secuflow.* TO 'secuflow'@'%';

-- Flush privileges
FLUSH PRIVILEGES;

-- Use database
USE secuflow;

-- Set character set
SET NAMES utf8mb4;

