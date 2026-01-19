# =============================================================================
# 监控与告警配置
# =============================================================================

# ---------- OpenTelemetry 遥测 ----------
# 启用后自动 instrument FastAPI、SQLAlchemy、httpx
TELEMETRY__ENABLED=false
# TELEMETRY__SAMPLING_RATE=1.0

# OTLP 导出（可选）
# TELEMETRY__TRACES_ENDPOINT=http://jaeger:4317
# TELEMETRY__LOGS_ENDPOINT=http://loki:3100
# TELEMETRY__METRICS_ENDPOINT=http://prometheus:9090

# ---------- 告警系统 ----------
ALERT__ENABLED=false
# 慢操作阈值
ALERT__SLOW_REQUEST_THRESHOLD=1.0
ALERT__SLOW_SQL_THRESHOLD=0.5
# 告警开关
ALERT__ALERT_ON_SLOW_REQUEST=true
ALERT__ALERT_ON_SLOW_SQL=true
ALERT__ALERT_ON_ERROR=true
# 慢请求排除路径（SSE/WebSocket 等长连接接口，支持 * 通配符）
# ALERT__SLOW_REQUEST_EXCLUDE_PATHS=["*/subscribe", "*/ws", "*/stream"]
# 聚合与抑制
ALERT__AGGREGATE_WINDOW=10
ALERT__SLOW_REQUEST_AGGREGATE=5
ALERT__SLOW_SQL_AGGREGATE=10
ALERT__EXCEPTION_AGGREGATE=1
ALERT__SUPPRESS_SECONDS=300

# ---------- 告警通知器（简版：单群）----------
# 所有告警发到同一个飞书群，取消注释并填写 Webhook 即可
# ALERT__NOTIFIERS__DEFAULT__TYPE=feishu
# ALERT__NOTIFIERS__DEFAULT__WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id
# ALERT__NOTIFIERS__DEFAULT__SECRET=your-secret

# ---------- 告警通知器（完整版：分群告警）----------
# 不同类型告警发到不同群，需配合 alert_rules.yaml 使用
# 生成规则模板：aury docs alert-rules
# ALERT__RULES_FILE=alert_rules.yaml

# 性能群（慢请求、慢SQL）
# ALERT__NOTIFIERS__PERF_GROUP__TYPE=feishu
# ALERT__NOTIFIERS__PERF_GROUP__WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/perf-webhook-id
# ALERT__NOTIFIERS__PERF_GROUP__SECRET=perf-secret

# 错误群（异常）
# ALERT__NOTIFIERS__ERROR_GROUP__TYPE=feishu
# ALERT__NOTIFIERS__ERROR_GROUP__WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/error-webhook-id
# ALERT__NOTIFIERS__ERROR_GROUP__SECRET=error-secret

# 运维群（任务失败、超时）
# ALERT__NOTIFIERS__OPS_GROUP__TYPE=feishu
# ALERT__NOTIFIERS__OPS_GROUP__WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/ops-webhook-id
# ALERT__NOTIFIERS__OPS_GROUP__SECRET=ops-secret

# 通用 Webhook（自定义系统）
# ALERT__NOTIFIERS__CUSTOM__TYPE=webhook
# ALERT__NOTIFIERS__CUSTOM__URL=https://your-system.com/api/alert
# ALERT__NOTIFIERS__CUSTOM__METHOD=POST
# ALERT__NOTIFIERS__CUSTOM__HEADERS={{"Authorization": "Bearer your-token"}}
