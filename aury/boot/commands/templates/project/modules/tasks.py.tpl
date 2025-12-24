"""异步任务模块（Dramatiq Worker）。

取消注释下面的示例代码即可启用异步任务。

使用方式：
    1. 配置 TASK_BROKER_URL 环境变量
    2. 取消注释下面的代码
    3. 运行 Worker：aury worker
    4. 在代码中调用：example_task.send()
"""

# from aury.boot.common.logging import logger
# from aury.boot.infrastructure.tasks import conditional_task
#
#
# @conditional_task()
# def example_task():
#     """示例异步任务。"""
#     logger.info("异步任务执行中...")
#     return {"status": "completed"}
