ALTER TABLE `vlm_tasks_item`
    ADD COLUMN `model_name` VARCHAR(255) NOT NULL DEFAULT ''
    COMMENT '执行时的模型名称快照'
    AFTER `model_id`;

UPDATE `vlm_tasks_item`
SET `model_name` = `model_id`
WHERE `model_name` = '';
