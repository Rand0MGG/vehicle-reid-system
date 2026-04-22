/*
  Project: Vehicle ReID System
  Purpose: Database bootstrap script

  This script only initializes database structure. It does not create users
  or seed administrator accounts.
*/

CREATE DATABASE IF NOT EXISTS vehicle_reid_db
  DEFAULT CHARSET utf8mb4
  COLLATE utf8mb4_general_ci;

USE vehicle_reid_db;

CREATE TABLE IF NOT EXISTS `sys_user` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'User primary key',
  `username` VARCHAR(50) NOT NULL COMMENT 'Login username',
  `password` VARCHAR(100) NOT NULL COMMENT 'Password hash',
  `role` VARCHAR(20) NOT NULL DEFAULT 'user' COMMENT 'Role: admin/user',
  `is_builtin` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Whether the account is protected',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Created at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sys_user_username` (`username`),
  CONSTRAINT `ck_sys_user_role` CHECK (`role` IN ('admin', 'user'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='System users';

CREATE TABLE IF NOT EXISTS `sys_log` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Log primary key',
  `user_id` INT DEFAULT NULL COMMENT 'Actor user ID',
  `operation` VARCHAR(100) NOT NULL COMMENT 'Operation summary',
  `status` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1=success, 0=failure',
  `exec_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Executed at',
  PRIMARY KEY (`id`),
  KEY `idx_sys_log_user_id` (`user_id`),
  KEY `idx_sys_log_exec_time` (`exec_time`),
  CONSTRAINT `fk_sys_log_user`
    FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Audit logs';

CREATE TABLE IF NOT EXISTS `system_config` (
  `config_key` VARCHAR(80) NOT NULL COMMENT 'Configuration key',
  `config_value` TEXT DEFAULT NULL COMMENT 'Serialized configuration value',
  `value_type` VARCHAR(20) NOT NULL DEFAULT 'string' COMMENT 'string/int/float/bool/json',
  `description` VARCHAR(255) DEFAULT NULL COMMENT 'Human readable description',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Updated at',
  PRIMARY KEY (`config_key`),
  CONSTRAINT `ck_system_config_value_type`
    CHECK (`value_type` IN ('string', 'int', 'float', 'bool', 'json'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='System configuration';

CREATE TABLE IF NOT EXISTS `vehicle_identity` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Vehicle identity primary key',
  `vehicle_code` VARCHAR(64) NOT NULL COMMENT 'Vehicle label parsed from image name',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Created at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_vehicle_identity_code` (`vehicle_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Vehicle identities';

CREATE TABLE IF NOT EXISTS `camera` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Camera primary key',
  `camera_code` VARCHAR(64) NOT NULL COMMENT 'Camera label parsed from image name',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Created at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_camera_code` (`camera_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Camera identities';

CREATE TABLE IF NOT EXISTS `gallery_image` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Gallery image primary key',
  `vehicle_identity_id` INT NOT NULL COMMENT 'Vehicle identity ID',
  `camera_id` INT NOT NULL COMMENT 'Camera ID',
  `capture_time` DATETIME DEFAULT NULL COMMENT 'Capture time parsed from filename',
  `img_path` VARCHAR(1024) NOT NULL COMMENT 'User-selected image path',
  `img_path_hash` CHAR(64) NOT NULL COMMENT 'SHA256 hash of normalized image path',
  `file_hash` CHAR(40) DEFAULT NULL COMMENT 'SHA1 hash of image bytes',
  `file_size` BIGINT DEFAULT NULL COMMENT 'Image file size in bytes',
  `width` INT DEFAULT NULL COMMENT 'Image width in pixels',
  `height` INT DEFAULT NULL COMMENT 'Image height in pixels',
  `created_by` INT DEFAULT NULL COMMENT 'User who registered the image',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Created at',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Updated at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gallery_image_path_hash` (`img_path_hash`),
  KEY `idx_gallery_image_vehicle` (`vehicle_identity_id`),
  KEY `idx_gallery_image_camera` (`camera_id`),
  KEY `idx_gallery_image_capture_time` (`capture_time`),
  KEY `idx_gallery_image_hash` (`file_hash`),
  KEY `idx_gallery_image_created_by` (`created_by`),
  CONSTRAINT `fk_gallery_image_vehicle`
    FOREIGN KEY (`vehicle_identity_id`) REFERENCES `vehicle_identity` (`id`)
    ON DELETE RESTRICT,
  CONSTRAINT `fk_gallery_image_camera`
    FOREIGN KEY (`camera_id`) REFERENCES `camera` (`id`)
    ON DELETE RESTRICT,
  CONSTRAINT `fk_gallery_image_created_by`
    FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Registered gallery images';

CREATE TABLE IF NOT EXISTS `model_profile` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Model profile primary key',
  `name` VARCHAR(80) NOT NULL COMMENT 'Display name',
  `description` TEXT DEFAULT NULL COMMENT 'Administrator notes',
  `is_enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Whether admins can use this profile',
  `is_public` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Whether users can select this profile',
  `display_order` INT NOT NULL DEFAULT 0 COMMENT 'Sort order',
  `active_revision_id` INT DEFAULT NULL COMMENT 'Current immutable model revision',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Created at',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Updated at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_profile_name` (`name`),
  KEY `idx_model_profile_enabled_public` (`is_enabled`, `is_public`, `display_order`),
  KEY `idx_model_profile_active_revision` (`active_revision_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Administrator maintained model profiles';

CREATE TABLE IF NOT EXISTS `model_revision` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Model revision primary key',
  `model_profile_id` INT NOT NULL COMMENT 'Owning model profile',
  `revision_name` VARCHAR(120) NOT NULL COMMENT 'Revision display name',
  `weights_file` VARCHAR(1024) NOT NULL COMMENT 'Weights path under outputs',
  `config_file` VARCHAR(1024) NOT NULL COMMENT 'Deployment config path',
  `supports_concat` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Whether Pro concat inference is supported',
  `supports_rerank` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Whether re-ranking is supported',
  `global_feature_dim` INT NOT NULL DEFAULT 2048 COMMENT 'Fast/global feature dimension',
  `full_feature_dim` INT NOT NULL DEFAULT 2048 COMMENT 'Stored full feature dimension',
  `fast_inference_mode` VARCHAR(32) NOT NULL DEFAULT 'global' COMMENT 'Inference mode used by Fast',
  `pro_inference_mode` VARCHAR(32) NOT NULL DEFAULT 'global_detail' COMMENT 'Inference mode used by Pro',
  `signature` CHAR(40) NOT NULL COMMENT 'Immutable revision signature',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Created at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_revision_signature` (`signature`),
  KEY `idx_model_revision_profile` (`model_profile_id`),
  CONSTRAINT `fk_model_revision_profile`
    FOREIGN KEY (`model_profile_id`) REFERENCES `model_profile` (`id`)
    ON DELETE RESTRICT,
  CONSTRAINT `ck_model_revision_global_dim` CHECK (`global_feature_dim` > 0),
  CONSTRAINT `ck_model_revision_full_dim` CHECK (`full_feature_dim` >= `global_feature_dim`),
  CONSTRAINT `ck_model_revision_concat_dim`
    CHECK (`supports_concat` = 1 OR `full_feature_dim` = `global_feature_dim`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Immutable model revisions';

SET @fk_model_profile_active_revision_exists := (
  SELECT COUNT(*)
  FROM information_schema.TABLE_CONSTRAINTS
  WHERE CONSTRAINT_SCHEMA = DATABASE()
    AND TABLE_NAME = 'model_profile'
    AND CONSTRAINT_NAME = 'fk_model_profile_active_revision'
);
SET @fk_model_profile_active_revision_sql := IF(
  @fk_model_profile_active_revision_exists = 0,
  'ALTER TABLE `model_profile` ADD CONSTRAINT `fk_model_profile_active_revision` FOREIGN KEY (`active_revision_id`) REFERENCES `model_revision` (`id`) ON DELETE SET NULL',
  'SELECT 1'
);
PREPARE fk_model_profile_active_revision_stmt FROM @fk_model_profile_active_revision_sql;
EXECUTE fk_model_profile_active_revision_stmt;
DEALLOCATE PREPARE fk_model_profile_active_revision_stmt;

CREATE TABLE IF NOT EXISTS `gallery_feature` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Gallery feature primary key',
  `image_id` INT NOT NULL COMMENT 'Gallery image ID',
  `model_revision_id` INT NOT NULL COMMENT 'Model revision used to extract this feature',
  `feature` LONGBLOB NOT NULL COMMENT 'Serialized full float32 feature vector',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Created at',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Updated at',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gallery_feature_image_revision` (`image_id`, `model_revision_id`),
  KEY `idx_gallery_feature_revision` (`model_revision_id`),
  KEY `idx_gallery_feature_image` (`image_id`),
  CONSTRAINT `fk_gallery_feature_image`
    FOREIGN KEY (`image_id`) REFERENCES `gallery_image` (`id`)
    ON DELETE RESTRICT,
  CONSTRAINT `fk_gallery_feature_revision`
    FOREIGN KEY (`model_revision_id`) REFERENCES `model_revision` (`id`)
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='One full feature vector per image and model revision';

CREATE TABLE IF NOT EXISTS `feature_build_task` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Feature build task primary key',
  `model_revision_id` INT NOT NULL COMMENT 'Target model revision',
  `triggered_by` INT DEFAULT NULL COMMENT 'Admin user who triggered the task',
  `mode` VARCHAR(20) NOT NULL DEFAULT 'incremental' COMMENT 'incremental/rebuild',
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/running/succeeded/failed/cancelled',
  `total_images` INT NOT NULL DEFAULT 0 COMMENT 'Total images to process',
  `processed_images` INT NOT NULL DEFAULT 0 COMMENT 'Processed image count',
  `success_count` INT NOT NULL DEFAULT 0 COMMENT 'Successful feature count',
  `failed_count` INT NOT NULL DEFAULT 0 COMMENT 'Failed image count',
  `message` TEXT DEFAULT NULL COMMENT 'Last status message',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Created at',
  `started_at` DATETIME DEFAULT NULL COMMENT 'Started at',
  `finished_at` DATETIME DEFAULT NULL COMMENT 'Finished at',
  PRIMARY KEY (`id`),
  KEY `idx_feature_build_task_revision` (`model_revision_id`),
  KEY `idx_feature_build_task_status` (`status`),
  KEY `idx_feature_build_task_triggered_by` (`triggered_by`),
  CONSTRAINT `fk_feature_build_task_revision`
    FOREIGN KEY (`model_revision_id`) REFERENCES `model_revision` (`id`)
    ON DELETE RESTRICT,
  CONSTRAINT `fk_feature_build_task_user`
    FOREIGN KEY (`triggered_by`) REFERENCES `sys_user` (`id`)
    ON DELETE SET NULL,
  CONSTRAINT `ck_feature_build_task_mode`
    CHECK (`mode` IN ('incremental', 'rebuild')),
  CONSTRAINT `ck_feature_build_task_status`
    CHECK (`status` IN ('pending', 'running', 'succeeded', 'failed', 'cancelled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Per-model gallery feature build tasks';
