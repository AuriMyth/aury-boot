# 监控与 Profiling

本文档介绍 {project_name} 项目中的监控和性能分析配置。

## 监控能力概览

| 功能 | 用途 | 建议环境 |
|------|------|----------|
| OpenTelemetry | 链路追踪、慢请求检测 | 所有环境 |
| 告警系统 | 异常/慢请求通知 | 所有环境 |
| Pyroscope | 持续 Profiling、火焰图 | 测试/灰度 |
| 阻塞检测 | 检测同步代码阻塞协程 | 测试/按需 |

---

## 不同环境的最佳实践

### 开发环境

```bash
# .env.development
TELEMETRY__ENABLED=false
ALERT__ENABLED=false
PROFILING__ENABLED=false
PROFILING__BLOCKING_DETECTOR_ENABLED=true  # 开发时检测阻塞问题
```

### 测试/灰度环境

```bash
# .env.staging
TELEMETRY__ENABLED=true
TELEMETRY__TRACES_ENDPOINT=http://jaeger:4317

ALERT__ENABLED=true
ALERT__NOTIFIERS__DEFAULT__TYPE=feishu
ALERT__NOTIFIERS__DEFAULT__WEBHOOK=https://...

# 开启 Profiling 排查性能问题
PROFILING__ENABLED=true
PROFILING__PYROSCOPE_ENDPOINT=http://pyroscope:4040

PROFILING__BLOCKING_DETECTOR_ENABLED=true
```

### 生产环境

```bash
# .env.production
# 链路追踪 - 必开
TELEMETRY__ENABLED=true
TELEMETRY__TRACES_ENDPOINT=http://jaeger:4317
TELEMETRY__SAMPLING_RATE=0.1  # 采样 10% 减少开销

# 告警 - 必开
ALERT__ENABLED=true
ALERT__NOTIFIERS__DEFAULT__TYPE=feishu
ALERT__NOTIFIERS__DEFAULT__WEBHOOK=https://...

# Profiling - 按需（有约 2-5% CPU 开销）
PROFILING__ENABLED=false  # 出问题时临时开启
# PROFILING__PYROSCOPE_ENDPOINT=http://pyroscope:4040
# PROFILING__PYROSCOPE_SAMPLE_RATE=10  # 降低采样率减少开销

# 阻塞检测 - 按需
PROFILING__BLOCKING_DETECTOR_ENABLED=false  # 出问题时临时开启
```

---

## OpenTelemetry

自动 instrument：
- FastAPI 请求
- SQLAlchemy SQL 查询
- httpx 外部调用

### 配置

```bash
TELEMETRY__ENABLED=true
TELEMETRY__TRACES_ENDPOINT=http://jaeger:4317  # 可选
TELEMETRY__SAMPLING_RATE=1.0  # 采样率，1.0=100%
```

### 手动 Span

```python
from aury.boot.infrastructure.monitoring.tracing import span, trace_span

# 装饰器方式
@trace_span(name="call_external_api")
async def call_api():
    ...

# 上下文管理器
async def process():
    with span("step_1"):
        await do_step_1()
    with span("step_2"):
        await do_step_2()
```

---

## Pyroscope 持续 Profiling

生成 CPU 火焰图，定位性能瓶颈。

### 安装

```bash
pip install pyroscope-io
```

### 配置

```bash
PROFILING__ENABLED=true
PROFILING__PYROSCOPE_ENDPOINT=http://pyroscope:4040
PROFILING__PYROSCOPE_SAMPLE_RATE=100  # 采样率 Hz
```

### 部署 Pyroscope

```yaml
# docker-compose.yml
services:
  pyroscope:
    image: grafana/pyroscope:latest
    ports:
      - "4040:4040"
```

访问 http://localhost:4040 查看火焰图。

---

## 事件循环阻塞检测

检测同步代码阻塞 asyncio 事件循环的问题。

### 安装

```bash
pip install psutil
```

### 配置

```bash
PROFILING__BLOCKING_DETECTOR_ENABLED=true
PROFILING__BLOCKING_THRESHOLD_MS=100       # 阻塞阈值
PROFILING__BLOCKING_SEVERE_THRESHOLD_MS=500  # 严重阈值
PROFILING__BLOCKING_ALERT_ENABLED=true     # 阻塞时发送告警
PROFILING__BLOCKING_ALERT_COOLDOWN_SECONDS=60  # 告警冷却
```

### 工作原理

1. 后台线程每 100ms 向事件循环投递空任务
2. 如果响应延迟 > 阈值，说明事件循环被阻塞
3. 自动捕获主线程调用栈 + 进程状态
4. 发送告警（含阻塞代码位置）

### 告警示例

```
事件循环阻塞(严重): 520ms

调用栈:
  app/services/sync_io.py:42 in read_file
    > data = open(path).read()  # 同步 IO！
  
进程状态:
  cpu: 95%, memory: 256MB, threads: 12
```

### 常见阻塞原因

- `time.sleep()` 应使用 `asyncio.sleep()`
- `open().read()` 应使用 `aiofiles`
- `requests.get()` 应使用 `httpx` 或 `aiohttp`
- CPU 密集计算 应使用 `run_in_executor()`

---

## 环境变量参考

### Telemetry

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TELEMETRY__ENABLED` | 是否启用 | `false` |
| `TELEMETRY__TRACES_ENDPOINT` | Traces 导出端点 | - |
| `TELEMETRY__LOGS_ENDPOINT` | Logs 导出端点 | - |
| `TELEMETRY__METRICS_ENDPOINT` | Metrics 导出端点 | - |
| `TELEMETRY__SAMPLING_RATE` | 采样率 | `1.0` |

### Profiling

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PROFILING__ENABLED` | 是否启用 Pyroscope | `false` |
| `PROFILING__PYROSCOPE_ENDPOINT` | Pyroscope 端点 | - |
| `PROFILING__PYROSCOPE_SAMPLE_RATE` | 采样率 (Hz) | `100` |
| `PROFILING__BLOCKING_DETECTOR_ENABLED` | 阻塞检测 | `false` |
| `PROFILING__BLOCKING_THRESHOLD_MS` | 阻塞阈值 | `100` |
| `PROFILING__BLOCKING_SEVERE_THRESHOLD_MS` | 严重阈值 | `500` |
| `PROFILING__BLOCKING_ALERT_ENABLED` | 阻塞告警 | `true` |
| `PROFILING__BLOCKING_ALERT_COOLDOWN_SECONDS` | 告警冷却 | `60` |

---

## 推荐的监控栈

### 开源方案

```
OpenTelemetry → Jaeger (Traces)
             → Grafana Loki (Logs)
             → Prometheus (Metrics)
             
Pyroscope → 火焰图
```

### 云服务方案

- **阿里云 ARMS** - APM + 告警
- **腾讯云 APM** - 类似
- **Datadog** - 全功能 APM
- **Sentry** - 错误监控

---

## 相关文档

- [17-alerting.md](./17-alerting.md) - 告警系统详细配置
- [11-logging.md](./11-logging.md) - 日志配置
