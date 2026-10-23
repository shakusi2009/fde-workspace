-- Initial TSP driver master-data table.
CREATE TABLE IF NOT EXISTS `tsp_drivers` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL COMMENT '姓名',
    `phone` VARCHAR(32) NOT NULL COMMENT '电话',
    `vin` VARCHAR(64) NOT NULL COMMENT 'VIN码',
    `vehicle_model` VARCHAR(100) NOT NULL COMMENT '车型',
    `address` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '联系地址',
    `registration_city` VARCHAR(100) NOT NULL COMMENT '注册城市',
    `registration_date` DATE NOT NULL COMMENT '注册日期',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_tsp_drivers_vin` (`vin`),
    KEY `idx_tsp_drivers_name` (`name`),
    KEY `idx_tsp_drivers_phone` (`phone`),
    KEY `idx_tsp_drivers_city` (`registration_city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='TSP车主信息';
