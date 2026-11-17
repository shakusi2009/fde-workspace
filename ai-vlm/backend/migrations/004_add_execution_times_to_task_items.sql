ALTER TABLE `vlm_tasks_item`
    ADD COLUMN `start_time` DATETIME(6) NULL
    COMMENT '任务执行开始时间'
    AFTER `task_status`,
    ADD COLUMN `end_time` DATETIME(6) NULL
    COMMENT '任务执行结束时间'
    AFTER `start_time`;
