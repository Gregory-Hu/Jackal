# 📦 GitHub 上传/下载指南

## 🚀 方法 1: 使用清理脚本（推荐）

### 上传前清理

```bash
# 1. 运行清理脚本
python cleanup_for_github.py

# 2. 确认清理结果
# 脚本会显示保留的文件结构

# 3. 复制整个目录到 GitHub 仓库
# 可以直接拖拽到 GitHub Desktop 或通过其他方式上传
```

### 下载后初始化

```bash
# 1. 复制 .env.example 为 .env
copy .env.example .env

# 2. 编辑 .env 填入 API Key
# LLM_API_KEY=your-api-key-here

# 3. 创建虚拟环境
python -m venv venv

# 4. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 5. 安装依赖
pip install -r requirements.txt

# 6. 创建工作目录
mkdir workspace

# 7. 运行测试
python test_migration.py
```

---

## 📁 文件结构说明

### ✅ 需要上传的文件

```
agent/
├── .gitignore              # Git 忽略配置
├── .env.example            # 环境变量示例
├── config.py               # 配置加载
├── requirements.txt        # Python 依赖
├── README.md               # 项目说明
├── MIGRATION_COMPLETE.md   # 迁移报告
├── cleanup_for_github.py   # 清理脚本
├── init_after_clone.py     # 初始化脚本
│
├── infra/                  # 基础设施层
│   ├── __init__.py
│   ├── messaging.py        # 内部消息总线
│   ├── registry.py         # 模块注册表
│   ├── mcp_config.py       # MCP 配置
│   ├── mcp_client.py       # MCP 客户端
│   └── fault.py            # Fault 检测与 Escalation
│
├── agents/                 # Agent 定义
│   ├── __init__.py
│   ├── base.py             # Agent 基类
│   ├── coder.py
│   └── reviewer.py
│
├── application/            # 应用层
│   ├── __init__.py
│   ├── orchestration.py    # 编排服务
│   ├── meeting.py          # 会议服务
│   └── reporting.py        # 报告服务
│
├── memory/                 # 记忆层
│   ├── __init__.py
│   └── memory_service.py   # 记忆服务
│
├── services/               # 服务层
│   └── __init__.py         # 导出 OpenHands Tools
│
├── tools/                  # 自定义工具
│   └── __init__.py         # 导出 OpenHands Tool 系统
│
├── jd/                     # Job Descriptions
│   ├── expert_microarch_analyst.md
│   ├── expert_microarch_analyst_resource.md
│   ├── junior_developer.md
│   └── senior_python_dev.md
│
├── skills/                 # 技能定义
│   └── fault_handling_escalation.md
│
├── sops/                   # 标准操作程序
├── duty_skills/            # 职责技能
├── orchestration_skills/   # 编排技能
├── examples/               # 示例代码
├── docs/                   # 文档
├── core/                   # 核心配置
├── orchestration/          # 编排模块
│
├── test_migration.py       # 迁移测试
└── test_fault_escalation.py # Fault 测试
```

### ❌ 不需要上传的文件

```
agent/
├── venv/                   # 虚拟环境（体积大，可重建）
├── __pycache__/            # Python 缓存
├── *.pyc                   # 编译后的文件
├── .env                    # 环境变量（含敏感信息）
├── workspace/              # 工作目录（运行时生成）
├── reports/                # 生成的报告
├── logs/                   # 日志文件
└── tmp/                    # 临时文件
```

---

## 🛠️ 方法 2: 手动清理

如果不想运行脚本，可以手动删除以下目录：

### Windows (PowerShell)

```powershell
# 删除虚拟环境
Remove-Item -Recurse -Force venv

# 删除缓存
Remove-Item -Recurse -Force __pycache__

# 删除工作目录
Remove-Item -Recurse -Force workspace
Remove-Item -Recurse -Force reports

# 删除临时文件
Remove-Item -Force .env -ErrorAction SilentlyContinue
```

### Linux/Mac (Bash)

```bash
# 删除虚拟环境
rm -rf venv

# 删除缓存
rm -rf __pycache__

# 删除工作目录
rm -rf workspace reports

# 删除临时文件
rm -f .env
```

---

## 📋 检查清单

上传前确认：

- [ ] 已删除 `venv/` 目录
- [ ] 已删除 `__pycache__/` 目录
- [ ] 已删除 `workspace/` 目录
- [ ] 已删除 `.env` 文件（但保留 `.env.example`）
- [ ] 已删除 `reports/` 目录
- [ ] 保留了 `requirements.txt`
- [ ] 保留了 `README.md`
- [ ] 保留了所有 `.py` 源文件
- [ ] 保留了所有 `.md` 文档

---

## 🎯 快速命令

```bash
# 清理（上传前）
python cleanup_for_github.py

# 初始化（下载后）
python init_after_clone.py

# 或者手动执行
copy .env.example .env
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📞 常见问题

### Q: 为什么不能上传 venv？
A: venv 包含大量第三方库文件（通常几百 MB），而且不同操作系统不兼容。其他人应该通过 `pip install -r requirements.txt` 重新安装。

### Q: .env 为什么不能上传？
A: .env 包含 API Key 等敏感信息，上传到 GitHub 会泄露密钥。应该上传 `.env.example` 作为模板。

### Q: 如何验证清理是否成功？
A: 运行 `cleanup_for_github.py` 后会显示保留的文件结构，确认没有 venv、__pycache__ 等目录即可。
