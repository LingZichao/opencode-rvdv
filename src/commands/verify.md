---
description: 启动RTL覆盖率验证任务
agent: coordinator
subtask: false
---

# 验证任务

请分析以下RTL模块的覆盖率不足问题并制定ISG脚本方案。

目标信息：
- RTL文件: **$1**
- 行号范围: **$2**
- 任务描述: $ARGUMENTS

## 执行步骤

1. 查询BASELINE覆盖率，确定未覆盖点
2. 识别模块的微架构行为
3. 设计原子化测试方案
4. 生成ISG脚本并编译
5. 执行仿真获取覆盖率
6. 分析结果并决定是否继续迭代