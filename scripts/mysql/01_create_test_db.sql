-- 仅在数据卷首次初始化时由 MySQL 官方镜像执行。
-- 创建集成测试专用库，并授权给业务账号；不授予全局权限，应用不使用 root。
CREATE DATABASE IF NOT EXISTS codepilot_edu_test
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

ALTER DATABASE codepilot_edu
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

GRANT ALL PRIVILEGES ON codepilot_edu_test.* TO 'codepilot'@'%';
FLUSH PRIVILEGES;
