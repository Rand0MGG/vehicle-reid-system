/*
  Project: Vehicle ReID System
  Purpose: Database bootstrap script
*/

CREATE DATABASE IF NOT EXISTS vehicle_reid_db
  DEFAULT CHARSET utf8mb4
  COLLATE utf8mb4_general_ci;

USE vehicle_reid_db;

CREATE TABLE IF NOT EXISTS `sys_user` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'User primary key',
  `username` VARCHAR(50) NOT NULL COMMENT 'Login username',
  `password` VARCHAR(100) NOT NULL COMMENT 'Password hash or bootstrap plaintext',
  `role` VARCHAR(20) DEFAULT 'user' COMMENT 'Role: admin/user',
  `is_builtin` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Whether the account is a protected builtin account',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Created at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='System users';

CREATE TABLE IF NOT EXISTS `vehicle_feature` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Record ID',
  `vehicle_id` VARCHAR(32) NOT NULL COMMENT 'Vehicle label',
  `cam_id` VARCHAR(32) NOT NULL COMMENT 'Camera ID',
  `capture_time` DATETIME NOT NULL COMMENT 'Capture time',
  `img_path` VARCHAR(255) NOT NULL COMMENT 'Relative image path',
  `feature` LONGBLOB NOT NULL COMMENT 'Serialized feature vector',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Created at',
  PRIMARY KEY (`id`),
  KEY `idx_vehicle_id` (`vehicle_id`),
  KEY `idx_capture_time` (`capture_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Gallery feature store';

CREATE TABLE IF NOT EXISTS `sys_log` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Log ID',
  `user_id` INT DEFAULT NULL COMMENT 'Actor user ID',
  `operation` VARCHAR(100) NOT NULL COMMENT 'Operation summary',
  `status` TINYINT(1) DEFAULT 1 COMMENT '1=success, 0=failure',
  `exec_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Executed at',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Audit logs';

INSERT INTO `sys_user` (`username`, `password`, `role`, `is_builtin`)
SELECT 'admin', 'admin123', 'admin', 1
FROM DUAL
WHERE NOT EXISTS (SELECT id FROM `sys_user` WHERE username = 'admin');
