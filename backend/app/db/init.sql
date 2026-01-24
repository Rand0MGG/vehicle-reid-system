/*
  项目名称：Vehicle ReID System
  用途：数据库初始化脚本
  对应文档：软件概要设计说明书 4.2 数据表定义
*/

-- 创建数据库 (如果不存在)
CREATE DATABASE IF NOT EXISTS vehicle_reid_db DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_general_ci;

USE vehicle_reid_db;

-- ----------------------------
-- 1. 用户信息表 (sys_user)
-- ----------------------------
CREATE TABLE IF NOT EXISTS `sys_user` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '用户唯一标识',
  `username` VARCHAR(50) NOT NULL COMMENT '登录账号',
  `password` VARCHAR(100) NOT NULL COMMENT '加密后的密码',
  `role` VARCHAR(20) DEFAULT 'user' COMMENT '角色权限: admin/user',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户信息表';

-- ----------------------------
-- 2. 车辆特征库表 (vehicle_feature)
-- 核心业务表，存储 2048 维特征向量 (BLOB)
-- ----------------------------
CREATE TABLE IF NOT EXISTS `vehicle_feature` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '记录流水号',
  `vehicle_id` VARCHAR(32) NOT NULL COMMENT '真实车辆ID (Label)',
  `cam_id` VARCHAR(32) NOT NULL COMMENT '摄像头编号',
  `capture_time` DATETIME NOT NULL COMMENT '车辆抓拍时间',
  `img_path` VARCHAR(255) NOT NULL COMMENT '图片相对路径',
  `feature` LONGBLOB NOT NULL COMMENT '序列化后的特征向量数据',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
  PRIMARY KEY (`id`),
  KEY `idx_vehicle_id` (`vehicle_id`),
  KEY `idx_capture_time` (`capture_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车辆特征库';

-- ----------------------------
-- 3. 系统日志表 (sys_log)
-- ----------------------------
CREATE TABLE IF NOT EXISTS `sys_log` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `user_id` INT DEFAULT NULL COMMENT '操作用户ID',
  `operation` VARCHAR(100) NOT NULL COMMENT '操作简述',
  `status` TINYINT(1) DEFAULT 1 COMMENT '状态 (1:成功, 0:失败)',
  `exec_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统日志表';

-- ----------------------------
-- 4. 初始化默认数据
-- ----------------------------
-- 插入一个默认管理员账号 (admin / admin123)
-- 使用 INSERT IGNORE 或 WHERE NOT EXISTS 防止重复插入报错
INSERT INTO `sys_user` (`username`, `password`, `role`) 
SELECT 'admin', 'admin123', 'admin' 
FROM DUAL 
WHERE NOT EXISTS (SELECT id FROM `sys_user` WHERE username = 'admin');