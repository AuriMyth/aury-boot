# 告警规则配置文件
#
# 使用方法：
#   1. 在 .env 中配置 ALERT__RULES_FILE=alert_rules.yaml
#   2. 配置通知器（见下方示例）
#   3. 根据需要修改规则
#
# 简版配置（所有告警发到同一个群）：
#   ALERT__NOTIFIERS__DEFAULT__TYPE=feishu
#   ALERT__NOTIFIERS__DEFAULT__WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
#
# 完整版配置（分群告警）：
#   ALERT__NOTIFIERS__PERF_GROUP__TYPE=feishu
#   ALERT__NOTIFIERS__PERF_GROUP__WEBHOOK=https://open.feishu.cn/.../perf-xxx
#   ALERT__NOTIFIERS__ERROR_GROUP__TYPE=feishu
#   ALERT__NOTIFIERS__ERROR_GROUP__WEBHOOK=https://open.feishu.cn/.../error-xxx
#   ALERT__NOTIFIERS__OPS_GROUP__TYPE=feishu
#   ALERT__NOTIFIERS__OPS_GROUP__WEBHOOK=https://open.feishu.cn/.../ops-xxx

defaults:
  slow_request_threshold: 1.0
  slow_sql_threshold: 0.5
  aggregate_window: 10
  suppress_seconds: 300

rules:
  # ============ 简版：所有告警发到 default 群 ============
  # 如果使用分群告警，请注释掉这部分，使用下方的完整版

  - name: slow_request
    event_types: [slow_request]
    aggregate_threshold: 5
    notifiers: [default]

  - name: slow_sql
    event_types: [slow_sql]
    aggregate_threshold: 10
    notifiers: [default]

  - name: exception
    event_types: [exception]
    aggregate_threshold: 1
    suppress_seconds: 60
    notifiers: [default]

  - name: task_issues
    event_types: [task_failure, task_timeout]
    aggregate_threshold: 1
    notifiers: [default]

  # ============ 完整版：分群告警 ============
  # 取消注释并配置对应的通知器即可使用

  # 慢请求 → 性能群
  # - name: slow_request
  #   event_types: [slow_request]
  #   aggregate_threshold: 5
  #   notifiers: [perf_group]

  # 慢 SQL → 性能群
  # - name: slow_sql
  #   event_types: [slow_sql]
  #   aggregate_threshold: 10
  #   notifiers: [perf_group]

  # 异常 → 错误群（立即告警）
  # - name: exception
  #   event_types: [exception]
  #   aggregate_threshold: 1
  #   suppress_seconds: 60
  #   notifiers: [error_group]

  # 任务失败/超时 → 运维群
  # - name: task_issues
  #   event_types: [task_failure, task_timeout]
  #   aggregate_threshold: 1
  #   notifiers: [ops_group]

  # 关键接口更严格的阈值（示例）
  # - name: critical_api
  #   event_types: [slow_request]
  #   path_pattern: "/api/v1/payments/*"
  #   threshold: 0.5
  #   aggregate_threshold: 1
  #   notifiers: [error_group]
