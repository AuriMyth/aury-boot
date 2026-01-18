# 告警系统

本文档介绍 {project_name} 项目中的告警系统配置和使用方法。

## 快速开始（简版配置）

所有告警发送到同一个飞书群：

```bash
# .env
ALERT__ENABLED=true
ALERT__NOTIFIERS__DEFAULT__TYPE=feishu
ALERT__NOTIFIERS__DEFAULT__WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

框架会自动创建默认规则，检测慢请求、慢 SQL、异常并发送告警。

---

## 完整版配置（分群告警）

不同类型的告警发送到不同的飞书群，避免一个群接收所有消息。

### 1. 环境变量

```bash
# .env

# ============ 告警系统 ============
ALERT__ENABLED=true
ALERT__RULES_FILE=alert_rules.yaml

# 性能群（慢请求、慢SQL）
ALERT__NOTIFIERS__PERF_GROUP__TYPE=feishu
ALERT__NOTIFIERS__PERF_GROUP__WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/perf-xxx
ALERT__NOTIFIERS__PERF_GROUP__SECRET=your-secret  # 可选

# 错误群（异常）
ALERT__NOTIFIERS__ERROR_GROUP__TYPE=feishu
ALERT__NOTIFIERS__ERROR_GROUP__WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/error-xxx

# 运维群（任务失败、超时）
ALERT__NOTIFIERS__OPS_GROUP__TYPE=feishu
ALERT__NOTIFIERS__OPS_GROUP__WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/ops-xxx

# 慢操作阈值
ALERT__SLOW_REQUEST_THRESHOLD=1.0
ALERT__SLOW_SQL_THRESHOLD=0.5
```

### 2. 规则文件

生成规则模板：`aury docs alert-rules`

```yaml
# alert_rules.yaml
defaults:
  slow_request_threshold: 1.0
  slow_sql_threshold: 0.5
  aggregate_window: 10
  suppress_seconds: 300

rules:
  # 慢请求 → 性能群
  - name: slow_request
    event_types: [slow_request]
    aggregate_threshold: 5
    notifiers: [perf_group]

  # 慢 SQL → 性能群
  - name: slow_sql
    event_types: [slow_sql]
    aggregate_threshold: 10
    notifiers: [perf_group]

  # 异常 → 错误群（立即告警）
  - name: exception
    event_types: [exception]
    aggregate_threshold: 1
    suppress_seconds: 60
    notifiers: [error_group]

  # 任务失败/超时 → 运维群
  - name: task_issues
    event_types: [task_failure, task_timeout]
    aggregate_threshold: 1
    notifiers: [ops_group]
```

### 3. 效果

| 事件类型 | 目标群 | 触发条件 |
|---------|--------|----------|
| 慢请求（>1s） | 性能群 | 60秒内累计5次 |
| 慢 SQL（>0.5s） | 性能群 | 60秒内累计10次 |
| 异常 | 错误群 | 立即告警 |
| 任务失败/超时 | 运维群 | 立即告警 |

---

## 代码中手动发送告警

```python
from aury.boot.infrastructure.monitoring.alerting import emit_alert, AlertEventType, AlertSeverity

# 发送自定义告警
await emit_alert(
    AlertEventType.CUSTOM,
    "订单支付超时",
    severity=AlertSeverity.WARNING,
    order_id="12345",
    user_id="u001",
)

# 发送慢 SQL 告警（通常由框架自动触发）
await emit_alert(
    AlertEventType.SLOW_SQL,
    "慢查询告警",
    duration=2.5,
    sql="SELECT * FROM orders WHERE ...",
)
```

---

## 通知器类型

### 飞书（feishu）

```bash
ALERT__NOTIFIERS__XXX__TYPE=feishu
ALERT__NOTIFIERS__XXX__WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
ALERT__NOTIFIERS__XXX__SECRET=xxx  # 可选，签名密钥
```

### 通用 Webhook

```bash
ALERT__NOTIFIERS__XXX__TYPE=webhook
ALERT__NOTIFIERS__XXX__URL=https://your-system.com/alert
ALERT__NOTIFIERS__XXX__METHOD=POST
ALERT__NOTIFIERS__XXX__HEADERS='{{"Authorization": "Bearer xxx"}}'
```

### 自定义通知器

```python
from aury.boot.infrastructure.monitoring.alerting import AlertNotifier, AlertManager

class DingTalkNotifier(AlertNotifier):
    @classmethod
    def from_config(cls, config: dict) -> "DingTalkNotifier":
        return cls(webhook=config["webhook"])

    async def send(self, notification) -> bool:
        # 实现发送逻辑
        ...

# 注册
AlertManager.register_notifier_class("dingtalk", DingTalkNotifier)
```

然后在环境变量中使用：

```bash
ALERT__NOTIFIERS__DING__TYPE=dingtalk
ALERT__NOTIFIERS__DING__WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
```

---

## 告警事件类型

| 类型 | 说明 | 自动触发 |
|-----|------|----------|
| `slow_request` | 慢 HTTP 请求 | 框架自动检测 |
| `slow_sql` | 慢 SQL 查询 | 框架自动检测 |
| `exception` | 异常/错误 | 框架自动检测 |
| `task_failure` | 任务执行失败 | 任务系统触发 |
| `task_timeout` | 任务执行超时 | 任务系统触发 |
| `custom` | 自定义告警 | 手动调用 emit_alert |

---

## 告警抑制与聚合

- **聚合窗口**：在窗口时间内累计触发次数，达到阈值才发送告警
- **抑制时间**：同一告警在抑制时间内不会重复发送
- **示例**：`aggregate_window=60, aggregate_threshold=5` 表示 60 秒内触发 5 次才告警

这样可以避免告警风暴，同时不遗漏重要问题。

---

## 环境变量参考

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ALERT__ENABLED` | 是否启用告警 | `false` |
| `ALERT__RULES_FILE` | 规则文件路径 | - |
| `ALERT__SLOW_REQUEST_THRESHOLD` | 慢请求阈值（秒） | `1.0` |
| `ALERT__SLOW_SQL_THRESHOLD` | 慢 SQL 阈值（秒） | `0.5` |
| `ALERT__ALERT_ON_SLOW_REQUEST` | 是否对慢请求告警 | `true` |
| `ALERT__ALERT_ON_SLOW_SQL` | 是否对慢 SQL 告警 | `true` |
| `ALERT__ALERT_ON_ERROR` | 是否对异常告警 | `true` |
| `ALERT__AGGREGATE_WINDOW` | 聚合窗口（秒） | `10` |
| `ALERT__SLOW_REQUEST_AGGREGATE` | 慢请求触发阈值（窗口内次数） | `5` |
| `ALERT__SLOW_SQL_AGGREGATE` | 慢 SQL 触发阈值 | `10` |
| `ALERT__EXCEPTION_AGGREGATE` | 异常触发阈值 | `1` |
| `ALERT__SUPPRESS_SECONDS` | 抑制时间（秒） | `300` |
