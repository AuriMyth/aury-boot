"""代码生成器命令。

生成符合 Aury 规范的代码文件：
- model: SQLAlchemy 模型
- repo: Repository 数据访问层
- service: Service 业务逻辑层
- api: FastAPI 路由
- schema: Pydantic 模型
- crud: 一键生成以上所有

支持两种字段定义模式：
1. 命令行参数（AI 友好）：
   aury generate model user email:str:unique age:int? status:str=active

2. 交互式（人类友好）：
   aury generate model user -i
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Annotated

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
import typer

from .config import get_project_config

console = Console()

# 模板目录
GENERATE_TEMPLATES_DIR = Path(__file__).parent / "templates" / "generate"

# 创建代码生成器子应用
app = typer.Typer(
    name="generate",
    help="代码生成器 - 生成 model/repo/service/api/schema",
    no_args_is_help=True,
)


# ============================================================
# 字段解析
# ============================================================

# 类型映射：简写 -> (SQLAlchemy 类型, Pydantic 类型, 需要的导入)
TYPE_MAPPING: dict[str, tuple[str, str, list[str]]] = {
    # 字符串
    "str": ("String(255)", "str", ["String"]),
    "string": ("String(255)", "str", ["String"]),
    "text": ("Text", "str", ["Text"]),
    # 数字
    "int": ("Integer", "int", ["Integer"]),
    "integer": ("Integer", "int", ["Integer"]),
    "bigint": ("BigInteger", "int", ["BigInteger"]),
    "float": ("Float", "float", ["Float"]),
    "decimal": ("Numeric(10, 2)", "Decimal", ["Numeric"]),
    # 布尔
    "bool": ("Boolean", "bool", ["Boolean"]),
    "boolean": ("Boolean", "bool", ["Boolean"]),
    # 日期时间
    "datetime": ("DateTime", "datetime", ["DateTime"]),
    "date": ("Date", "date", ["Date"]),
    "time": ("Time", "time", ["Time"]),
    # JSON
    "json": ("JSON", "dict", ["JSON"]),
    "dict": ("JSON", "dict", ["JSON"]),
    # UUID
    "uuid": ("GUID", "str", []),  # 使用框架内置 GUID
}


@dataclass
class FieldDefinition:
    """字段定义。"""

    name: str
    type_name: str = "str"
    nullable: bool = False
    unique: bool = False
    index: bool = False
    default: str | None = None
    max_length: int | None = None  # 用于 str 类型
    comment: str | None = None

    @classmethod
    def parse(cls, spec: str) -> "FieldDefinition":
        """解析字段定义字符串。

        格式: name:type:modifiers
        修饰符:
        - ? 或 nullable: 可空
        - unique: 唯一
        - index: 索引
        - =value: 默认值
        - (length): 长度限制

        示例:
        - email:str:unique
        - age:int?
        - status:str=active
        - name:str(100)
        - bio:text?
        - price:decimal:index
        """
        parts = spec.split(":")
        name = parts[0]

        # 默认类型为 str
        type_name = "str"
        nullable = False
        unique = False
        index = False
        default = None
        max_length = None

        for part in parts[1:]:
            # 检查是否是类型定义
            type_match = re.match(r"^([a-z]+)(\((\d+)\))?$", part.lower())
            if type_match and type_match.group(1) in TYPE_MAPPING:
                type_name = type_match.group(1)
                if type_match.group(3):
                    max_length = int(type_match.group(3))
                continue

            # 检查修饰符
            part_lower = part.lower()
            if part_lower in ("?", "nullable"):
                nullable = True
            elif part_lower == "unique":
                unique = True
            elif part_lower == "index":
                index = True
            elif part.startswith("="):
                default = part[1:]
            elif part.endswith("?"):
                # 处理 age:int? 这种格式
                type_check = part[:-1].lower()
                if type_check in TYPE_MAPPING:
                    type_name = type_check
                    nullable = True

        # 处理名字后面直接跟 ? 的情况，如 "age?"
        if name.endswith("?"):
            name = name[:-1]
            nullable = True

        return cls(
            name=name,
            type_name=type_name,
            nullable=nullable,
            unique=unique,
            index=index,
            default=default,
            max_length=max_length,
        )


# 可用的模型基类
# id_type: "int" | "uuid" 用于生成正确的 Schema/Service/API 类型
MODEL_BASE_CLASSES = {
    "IDOnlyModel": {
        "desc": "纯 int 主键（无时间戳，适合关系表）",
        "features": ["id: int"],
        "id_type": "int",
        "has_timestamps": False,
    },
    "UUIDOnlyModel": {
        "desc": "纯 UUID 主键（无时间戳，适合关系表）",
        "features": ["id: UUID"],
        "id_type": "uuid",
        "has_timestamps": False,
    },
    "Model": {
        "desc": "标准模型（int主键 + 时间戳）",
        "features": ["id: int", "created_at", "updated_at"],
        "id_type": "int",
        "has_timestamps": True,
    },
    "AuditableStateModel": {
        "desc": "标准模型 + 软删除",
        "features": ["id: int", "created_at", "updated_at", "deleted_at"],
        "id_type": "int",
        "has_timestamps": True,
    },
    "UUIDModel": {
        "desc": "UUID 主键模型",
        "features": ["id: UUID", "created_at", "updated_at"],
        "id_type": "uuid",
        "has_timestamps": True,
    },
    "UUIDAuditableStateModel": {
        "desc": "UUID 主键 + 软删除（推荐）",
        "features": ["id: UUID", "created_at", "updated_at", "deleted_at"],
        "id_type": "uuid",
        "has_timestamps": True,
    },
    "VersionedModel": {
        "desc": "乐观锁模型（int主键 + version）",
        "features": ["id: int", "version"],
        "id_type": "int",
        "has_timestamps": False,
    },
    "VersionedTimestampedModel": {
        "desc": "乐观锁 + 时间戳",
        "features": ["id: int", "created_at", "updated_at", "version"],
        "id_type": "int",
        "has_timestamps": True,
    },
    "VersionedUUIDModel": {
        "desc": "UUID + 乐观锁 + 时间戳",
        "features": ["id: UUID", "created_at", "updated_at", "version"],
        "id_type": "uuid",
        "has_timestamps": True,
    },
    "FullFeaturedModel": {
        "desc": "完整功能 int版",
        "features": ["id: int", "created_at", "updated_at", "deleted_at", "version"],
        "id_type": "int",
        "has_timestamps": True,
    },
    "FullFeaturedUUIDModel": {
        "desc": "完整功能 UUID版",
        "features": ["id: UUID", "created_at", "updated_at", "deleted_at", "version"],
        "id_type": "uuid",
        "has_timestamps": True,
    },
}

# UUID 类型的基类名称
UUID_BASE_CLASSES = {k for k, v in MODEL_BASE_CLASSES.items() if v.get("id_type") == "uuid"}


@dataclass
class ModelDefinition:
    """模型定义。"""

    name: str
    fields: list[FieldDefinition] = field(default_factory=list)
    soft_delete: bool = True
    timestamps: bool = True
    base_class: str | None = None  # 用户指定的基类

    @property
    def id_type(self) -> str:
        """获取 id 类型：'int' 或 'uuid'。"""
        if self.base_class:
            return MODEL_BASE_CLASSES.get(self.base_class, {}).get("id_type", "uuid")
        # 默认通过 soft_delete/timestamps 推断时使用 UUID
        return "uuid"

    @property
    def id_py_type(self) -> str:
        """获取 Python/Pydantic 的 id 类型。"""
        return "int" if self.id_type == "int" else "UUID"

    @property
    def has_timestamps(self) -> bool:
        """是否有时间戳字段。"""
        if self.base_class:
            return MODEL_BASE_CLASSES.get(self.base_class, {}).get("has_timestamps", True)
        return self.timestamps

    @property
    def class_name(self) -> str:
        """PascalCase 类名。"""
        return _to_pascal_case(self.name)

    @property
    def file_name(self) -> str:
        """snake_case 文件名。"""
        return _to_snake_case(self.name)

    @property
    def table_name(self) -> str:
        """snake_case 复数表名。"""
        return _to_plural(self.file_name)

    @property
    def var_name(self) -> str:
        """变量名。"""
        return self.file_name

    @property
    def var_name_plural(self) -> str:
        """复数变量名。"""
        return _to_plural(self.file_name)


# ============================================================
# 工具函数
# ============================================================


def _to_snake_case(name: str) -> str:
    """转换为 snake_case。"""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _to_pascal_case(name: str) -> str:
    """转换为 PascalCase。"""
    snake = _to_snake_case(name)
    return "".join(word.capitalize() for word in snake.split("_"))


def _to_plural(name: str) -> str:
    """简单的复数转换。"""
    if name.endswith("y"):
        return name[:-1] + "ies"
    if name.endswith(("s", "x", "ch", "sh")):
        return name + "es"
    return name + "s"


def _create_file(path: Path, content: str, force: bool = False) -> bool:
    """创建文件。"""
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _update_init_file(init_path: Path, import_line: str, export_name: str) -> None:
    """更新 __init__.py 文件。"""
    if not init_path.exists():
        init_path.write_text(
            f'{import_line}\n\n__all__ = ["{export_name}"]\n', encoding="utf-8"
        )
        return

    content = init_path.read_text(encoding="utf-8")

    # 检查是否已导入
    if import_line in content:
        return

    # 添加导入
    if "__all__" in content:
        content = content.replace("__all__", f"{import_line}\n\n__all__")
        if f'"{export_name}"' not in content:
            content = content.replace("__all__ = [", f'__all__ = [\n    "{export_name}",')
    else:
        content += f'\n{import_line}\n\n__all__ = ["{export_name}"]\n'

    init_path.write_text(content, encoding="utf-8")


# ============================================================
# 交互式字段收集
# ============================================================


def _collect_base_class_interactive() -> str:
    """交互式选择模型基类。"""
    console.print("\n[bold cyan]📚 选择模型基类[/bold cyan]\n")
    
    # 显示可用基类
    table = Table(title="可用模型基类", show_header=True, header_style="bold magenta")
    table.add_column("序号", style="dim", width=4)
    table.add_column("基类名", style="cyan")
    table.add_column("说明")
    table.add_column("自动继承的字段")
    
    base_names = list(MODEL_BASE_CLASSES.keys())
    for i, name in enumerate(base_names, 1):
        info = MODEL_BASE_CLASSES[name]
        # 推荐的加标记
        desc = info["desc"]
        if name == "UUIDAuditableStateModel":
            desc = f"[bold green]★ {desc}[/bold green]"
        table.add_row(str(i), name, desc, ", ".join(info["features"]))
    
    console.print(table)
    console.print()
    
    # 默认选择 UUIDAuditableStateModel（第 4 个）
    choice = Prompt.ask(
        "请选择基类序号",
        default="4",
        choices=[str(i) for i in range(1, len(base_names) + 1)],
    )
    
    selected = base_names[int(choice) - 1]
    console.print(f"  [green]✓ 已选择: {selected}[/green]\n")
    return selected


def _collect_fields_interactive() -> list[FieldDefinition]:
    """交互式收集字段定义。"""
    fields: list[FieldDefinition] = []

    console.print("\n[bold cyan]📝 添加字段[/bold cyan] (输入空名称结束)\n")

    # 显示类型帮助
    table = Table(title="支持的类型", show_header=True, header_style="bold magenta")
    table.add_column("类型", style="cyan")
    table.add_column("说明")
    table.add_row("str, string", "字符串 (默认)")
    table.add_row("text", "长文本")
    table.add_row("int, integer", "整数")
    table.add_row("bigint", "大整数")
    table.add_row("float", "浮点数")
    table.add_row("decimal", "精确小数")
    table.add_row("bool, boolean", "布尔值")
    table.add_row("datetime", "日期时间")
    table.add_row("date", "日期")
    table.add_row("json, dict", "JSON 对象")
    console.print(table)
    console.print()

    while True:
        name = Prompt.ask("[bold]字段名[/bold]", default="")
        if not name:
            break

        type_name = Prompt.ask(
            "  类型",
            default="str",
            choices=list(TYPE_MAPPING.keys()),
        )

        nullable = Confirm.ask("  可空?", default=False)
        unique = Confirm.ask("  唯一?", default=False)
        index = Confirm.ask("  索引?", default=False)
        default = Prompt.ask("  默认值 (留空无默认)", default="")

        max_length = None
        if type_name in ("str", "string"):
            length_str = Prompt.ask("  最大长度", default="255")
            max_length = int(length_str) if length_str.isdigit() else 255

        fields.append(
            FieldDefinition(
                name=name,
                type_name=type_name,
                nullable=nullable,
                unique=unique,
                index=index,
                default=default if default else None,
                max_length=max_length,
            )
        )

        console.print(f"  [green]✓ 已添加: {name}:{type_name}[/green]\n")

    return fields


# ============================================================
# 模板读取
# ============================================================


def _read_generate_template(name: str) -> str:
    """读取代码生成模板文件。"""
    template_path = GENERATE_TEMPLATES_DIR / name
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件不存在: {name} (查找路径: {GENERATE_TEMPLATES_DIR})")
    return template_path.read_text(encoding="utf-8")


def _get_base_class_from_model_file(code_root: Path, model_name: str) -> str | None:
    """从已生成的模型文件中读取基类名称。
    
    Args:
        code_root: 代码根目录
        model_name: 模型名称（snake_case）
    
    Returns:
        基类名称，如果无法读取则返回 None
    """
    model_file = code_root / "models" / f"{model_name}.py"
    if not model_file.exists():
        return None
    
    try:
        content = model_file.read_text(encoding="utf-8")
        # 查找继承的基类，例如: class User(UUIDAuditableStateModel):
        pattern = r"class\s+\w+\s*\((\w+)\)"
        match = re.search(pattern, content)
        if match:
            base_class = match.group(1)
            # 验证是否是有效的基类
            if base_class in MODEL_BASE_CLASSES:
                return base_class
    except Exception:
        pass
    
    return None


# ============================================================
# 模板生成
# ============================================================


def _generate_model_content(model: ModelDefinition) -> str:
    """生成 Model 内容。"""
    # 收集需要的导入
    imports: set[str] = {"String"}  # 默认总是有 String
    for f in model.fields:
        type_info = TYPE_MAPPING.get(f.type_name, ("String(255)", "str", ["String"]))
        imports.update(type_info[2])

    imports_str = ", ".join(sorted(imports))

    # 生成字段定义
    field_lines = []
    for f in model.fields:
        type_info = TYPE_MAPPING.get(f.type_name, ("String(255)", "str", ["String"]))
        sa_type = type_info[0]
        py_type = type_info[1]

        # 处理字符串长度
        if f.type_name in ("str", "string") and f.max_length:
            sa_type = f"String({f.max_length})"

        # 构建 Mapped 类型
        if f.nullable:
            mapped_type = f"Mapped[{py_type} | None]"
        else:
            mapped_type = f"Mapped[{py_type}]"

        # 构建 mapped_column 参数
        col_args = [sa_type]
        if f.unique:
            col_args.append("unique=True")
        if f.index:
            col_args.append("index=True")
        if f.nullable:
            col_args.append("nullable=True")
        if f.default is not None:
            if f.type_name in ("str", "string", "text"):
                col_args.append(f'default="{f.default}"')
            elif f.type_name in ("bool", "boolean"):
                col_args.append(f"default={f.default.capitalize()}")
            else:
                col_args.append(f"default={f.default}")

        col_args_str = ", ".join(col_args)
        field_lines.append(f"    {f.name}: {mapped_type} = mapped_column({col_args_str})")

    fields_str = "\n".join(field_lines) if field_lines else "    # 添加字段"

    # 选择基类：优先使用用户指定的，否则根据选项推断
    if model.base_class:
        base_class = model.base_class
        base_info = MODEL_BASE_CLASSES.get(base_class, {})
        features = base_info.get("features", [])
        base_doc = f"继承 {base_class} 自动获得：\n    - " + "\n    - ".join(features) if features else f"继承 {base_class} 基类。"
    elif model.soft_delete and model.timestamps:
        base_class = "UUIDAuditableStateModel"
        base_doc = """继承 UUIDAuditableStateModel 自动获得：
    - id: UUID 主键
    - created_at: 创建时间
    - updated_at: 更新时间
    - deleted_at: 软删除时间戳"""
    elif model.timestamps:
        base_class = "UUIDModel"
        base_doc = """继承 UUIDModel 自动获得：
    - id: UUID 主键
    - created_at: 创建时间
    - updated_at: 更新时间"""
    else:
        base_class = "Model"
        base_doc = "继承 Model 基类。"

    template = _read_generate_template("model.py.tpl")
    return template.format(
        class_name=model.class_name,
        imports_str=imports_str,
        base_class=base_class,
        base_doc=base_doc,
        table_name=model.table_name,
        fields_str=fields_str,
    )


def _generate_schema_content(model: ModelDefinition) -> str:
    """生成 Schema 内容。"""
    # 基础字段
    base_fields = []
    update_fields = []

    for f in model.fields:
        type_info = TYPE_MAPPING.get(f.type_name, ("String(255)", "str", ["String"]))
        py_type = type_info[1]

        # Base 字段（Create 继承）
        if f.nullable:
            field_type = f"{py_type} | None"
            default = "None"
        elif f.default is not None:
            field_type = py_type
            if f.type_name in ("str", "string", "text"):
                default = f'"{f.default}"'
            elif f.type_name in ("bool", "boolean"):
                default = f.default.capitalize()
            else:
                default = f.default
        else:
            field_type = py_type
            default = "..."

        # 构建 Field 参数
        field_args = [default]
        if f.type_name in ("str", "string") and f.max_length:
            field_args.append(f"max_length={f.max_length}")
        field_args.append(f'description="{f.name}"')

        field_args_str = ", ".join(field_args)
        base_fields.append(f"    {f.name}: {field_type} = Field({field_args_str})")

        # Update 字段（全部可选）
        update_field_args = ["None"]
        if f.type_name in ("str", "string") and f.max_length:
            update_field_args.append(f"max_length={f.max_length}")
        update_field_args.append(f'description="{f.name}"')
        update_field_args_str = ", ".join(update_field_args)
        update_fields.append(
            f"    {f.name}: {py_type} | None = Field({update_field_args_str})"
        )

    base_fields_str = "\n".join(base_fields) if base_fields else "    pass"
    update_fields_str = "\n".join(update_fields) if update_fields else "    pass"

    # Response 字段（继承 Base，添加 id 和时间戳）
    id_type = model.id_py_type  # "int" 或 "UUID"
    
    # 根据是否有时间戳生成不同的 response 字段
    if model.has_timestamps:
        response_extra = f'''    id: {id_type} = Field(..., description="ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")'''
    else:
        response_extra = f'    id: {id_type} = Field(..., description="ID")'

    # 导入语句
    imports = ["from datetime import datetime"] if model.has_timestamps else []
    if id_type == "UUID":
        imports.append("from uuid import UUID")
    imports_str = "\n".join(imports)
    if imports_str:
        imports_str += "\n"

    template = _read_generate_template("schema.py.tpl")
    return template.format(
        class_name=model.class_name,
        imports_str=imports_str,
        base_fields_str=base_fields_str,
        update_fields_str=update_fields_str,
        response_extra=response_extra,
    )


def _generate_repository_content(model: ModelDefinition, import_prefix: str = "") -> str:
    """生成 Repository 内容。

    Args:
        model: 模型定义
        import_prefix: import 前缀，如 "mypackage." 或 ""
    """
    # 查找唯一字段生成 get_by_xxx 方法
    get_by_methods = []
    for f in model.fields:
        if f.unique:
            type_info = TYPE_MAPPING.get(f.type_name, ("String(255)", "str", ["String"]))
            py_type = type_info[1]
            get_by_methods.append(f'''
    async def get_by_{f.name}(self, {f.name}: {py_type}) -> {model.class_name} | None:
        """按 {f.name} 获取。"""
        return await self.get_by({f.name}={f.name})''')

    methods_str = "\n".join(get_by_methods) if get_by_methods else ""

    template = _read_generate_template("repository.py.tpl")
    return template.format(
        class_name=model.class_name,
        import_prefix=import_prefix,
        file_name=model.file_name,
        methods_str=methods_str,
    )


def _generate_service_content(model: ModelDefinition, import_prefix: str = "") -> str:
    """生成 Service 内容。

    Args:
        model: 模型定义
        import_prefix: import 前缀，如 "mypackage." 或 ""
    """
    # 检查唯一字段，生成重复检测
    unique_checks = []
    for f in model.fields:
        if f.unique:
            unique_checks.append(
                f'''        # 检查 {f.name} 是否已存在
        existing = await self.repo.get_by_{f.name}(data.{f.name})
        if existing:
            raise AlreadyExistsError(f"{model.class_name} 已存在: {{data.{f.name}}}")
'''
            )

    unique_check_str = "\n".join(unique_checks) if unique_checks else ""
    
    # UUID 类型需要导入
    id_type = model.id_py_type
    uuid_import = "from uuid import UUID\n\n" if id_type == "UUID" else ""

    template = _read_generate_template("service.py.tpl")
    return template.format(
        class_name=model.class_name,
        uuid_import=uuid_import,
        import_prefix=import_prefix,
        file_name=model.file_name,
        id_py_type=model.id_py_type,
        unique_check_str=unique_check_str,
    )


def _generate_api_content(model: ModelDefinition, import_prefix: str = "") -> str:
    """生成 API 内容。

    Args:
        model: 模型定义
        import_prefix: import 前缀，如 "mypackage." 或 ""
    """
    id_type = model.id_py_type  # "int" 或 "UUID"
    
    # 导入语句
    imports = []
    if id_type == "UUID":
        imports.append("from uuid import UUID")
    imports_str = "\n".join(imports)
    if imports_str:
        imports_str += "\n"
    
    template = _read_generate_template("api.py.tpl")
    return template.format(
        class_name=model.class_name,
        uuid_import=imports_str,  # 模板中使用 uuid_import 占位符，但实际传入的是 imports_str（可能为空）
        import_prefix=import_prefix,
        file_name=model.file_name,
        var_name_plural=model.var_name_plural,
        var_name=model.var_name,
        id_type=id_type,
    )


# ============================================================
# 命令
# ============================================================


@app.command(name="model")
def generate_model(
    name: str = typer.Argument(..., help="模型名称（如 user, UserProfile）"),
    fields: Annotated[
        list[str] | None,
        typer.Argument(
            help="字段定义，格式: name:type:modifiers（如 email:str:unique age:int?）"
        ),
    ] = None,
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="交互式添加字段"
    ),
    base: str | None = typer.Option(
        None, "--base", "-b",
        help="模型基类（Model/UUIDModel/UUIDAuditableStateModel/VersionedModel 等）"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖"),
    no_soft_delete: bool = typer.Option(False, "--no-soft-delete", help="禁用软删除"),
    no_timestamps: bool = typer.Option(False, "--no-timestamps", help="禁用时间戳"),
) -> None:
    """生成 SQLAlchemy 模型。

    支持两种模式：

    1. 命令行参数（AI 友好）:
        aury generate model user email:str:unique age:int? status:str=active

    2. 交互式（人类友好）:
        aury generate model user -i

    字段语法：
        name:type:modifiers

    支持的类型：
        str, text, int, bigint, float, decimal, bool, datetime, date, json

    修饰符：
        ? 或 nullable  - 可空
        unique         - 唯一约束
        index          - 索引
        =value         - 默认值
        (length)       - 字符串长度，如 str(100)

    可用基类：
        Model, AuditableStateModel, UUIDModel, UUIDAuditableStateModel,
        VersionedModel, VersionedTimestampedModel, VersionedUUIDModel,
        FullFeaturedModel, FullFeaturedUUIDModel

    示例：
        aury generate model user
        aury generate model user -b VersionedUUIDModel
        aury generate model user email:str:unique age:int?
        aury generate model article title:str(200) content:text status:str=draft
    """
    base_path = Path.cwd()

    # 读取项目配置
    config = get_project_config(base_path)
    code_root = config.get_package_dir(base_path)

    # 解析字段
    field_defs: list[FieldDefinition] = []
    selected_base_class: str | None = base

    if interactive:
        # 交互式模式：先选择基类，再添加字段
        selected_base_class = _collect_base_class_interactive()
        field_defs = _collect_fields_interactive()
    elif fields:
        for spec in fields:
            try:
                field_defs.append(FieldDefinition.parse(spec))
            except Exception as e:
                console.print(f"[red]❌ 解析字段失败: {spec} - {e}[/red]")
                raise typer.Exit(1) from e

    # 验证基类名称
    if selected_base_class and selected_base_class not in MODEL_BASE_CLASSES:
        console.print(f"[red]❌ 无效的基类: {selected_base_class}[/red]")
        console.print(f"[dim]可用基类: {', '.join(MODEL_BASE_CLASSES.keys())}[/dim]")
        raise typer.Exit(1)

    model = ModelDefinition(
        name=name,
        fields=field_defs,
        soft_delete=not no_soft_delete,
        timestamps=not no_timestamps,
        base_class=selected_base_class,
    )

    content = _generate_model_content(model)
    file_path = code_root / "models" / f"{model.file_name}.py"
    rel_path = file_path.relative_to(base_path)

    if _create_file(file_path, content, force):
        console.print(f"[green]✅ 创建模型: {rel_path}[/green]")
        _update_init_file(
            code_root / "models" / "__init__.py",
            f"from .{model.file_name} import {model.class_name}",
            model.class_name,
        )
    else:
        console.print(
            f"[yellow]⚠️  文件已存在: {rel_path}（使用 --force 覆盖）[/yellow]"
        )


@app.command(name="repo")
def generate_repo(
    name: str = typer.Argument(..., help="模型名称"),
    fields: Annotated[
        list[str] | None,
        typer.Argument(help="字段定义（用于生成 get_by_xxx 方法）"),
    ] = None,
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖"),
) -> None:
    """生成 Repository 数据访问层。

    示例：
        aury generate repo user
        aury generate repo user email:str:unique  # 生成 get_by_email 方法
    """
    base_path = Path.cwd()

    # 读取项目配置
    config = get_project_config(base_path)
    code_root = config.get_package_dir(base_path)
    import_prefix = config.get_import_prefix()

    field_defs = [FieldDefinition.parse(spec) for spec in (fields or [])]
    # 尝试从已生成的模型文件中读取基类信息
    base_class = _get_base_class_from_model_file(code_root, _to_snake_case(name))
    model = ModelDefinition(name=name, fields=field_defs, base_class=base_class)

    content = _generate_repository_content(model, import_prefix)
    file_path = code_root / "repositories" / f"{model.file_name}_repository.py"
    rel_path = file_path.relative_to(base_path)

    if _create_file(file_path, content, force):
        console.print(f"[green]✅ 创建仓储: {rel_path}[/green]")
        _update_init_file(
            code_root / "repositories" / "__init__.py",
            f"from .{model.file_name}_repository import {model.class_name}Repository",
            f"{model.class_name}Repository",
        )
    else:
        console.print("[yellow]⚠️  文件已存在（使用 --force 覆盖）[/yellow]")


@app.command(name="service")
def generate_service(
    name: str = typer.Argument(..., help="模型名称"),
    fields: Annotated[
        list[str] | None,
        typer.Argument(help="字段定义（用于生成重复检测）"),
    ] = None,
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖"),
) -> None:
    """生成 Service 业务逻辑层。

    示例：
        aury generate service user
        aury generate service user email:str:unique  # 创建时检查 email 重复
    """
    base_path = Path.cwd()

    # 读取项目配置
    config = get_project_config(base_path)
    code_root = config.get_package_dir(base_path)
    import_prefix = config.get_import_prefix()

    field_defs = [FieldDefinition.parse(spec) for spec in (fields or [])]
    # 尝试从已生成的模型文件中读取基类信息
    base_class = _get_base_class_from_model_file(code_root, _to_snake_case(name))
    model = ModelDefinition(name=name, fields=field_defs, base_class=base_class)

    content = _generate_service_content(model, import_prefix)
    file_path = code_root / "services" / f"{model.file_name}_service.py"
    rel_path = file_path.relative_to(base_path)

    if _create_file(file_path, content, force):
        console.print(f"[green]✅ 创建服务: {rel_path}[/green]")
        _update_init_file(
            code_root / "services" / "__init__.py",
            f"from .{model.file_name}_service import {model.class_name}Service",
            f"{model.class_name}Service",
        )
    else:
        console.print("[yellow]⚠️  文件已存在（使用 --force 覆盖）[/yellow]")


def _register_router_in_api_init(code_root: Path, model: ModelDefinition) -> bool:
    """自动在 api/__init__.py 中注册路由。
    
    Args:
        code_root: 代码根目录（包含 api/ 的目录）
        model: 模型定义
    
    Returns:
        是否成功注册
    """
    api_init_path = code_root / "api" / "__init__.py"
    if not api_init_path.exists():
        return False
    
    content = api_init_path.read_text(encoding="utf-8")
    
    # 检查是否已经注册
    import_line = f"from . import {model.file_name}"
    router_line = f"router.include_router({model.file_name}.router)"
    
    if import_line in content or f"{model.file_name}.router" in content:
        return False  # 已经注册
    
    # 查找插入位置：在 "# 注册子路由" 标记之后
    marker = "# 注册子路由"
    
    if marker not in content:
        return False
    
    try:
        # 在标记之后插入
        lines = content.split("\n")
        new_lines = []
        inserted = False
        
        for line in lines:
            new_lines.append(line)
            if marker in line and not inserted:
                new_lines.append(import_line)
                new_lines.append(router_line)
                inserted = True
        
        if inserted:
            api_init_path.write_text("\n".join(new_lines), encoding="utf-8")
            return True
    except Exception:
        pass  # 插入失败不影响主流程
    
    return False


@app.command(name="api")
def generate_api(
    name: str = typer.Argument(..., help="模型名称"),
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖"),
    no_register: bool = typer.Option(False, "--no-register", help="不自动注册到 api/__init__.py"),
) -> None:
    """生成 FastAPI 路由。

    示例：
        aury generate api user
        aury generate api user --no-register  # 不自动注册到 api/__init__.py
    """
    base_path = Path.cwd()

    # 读取项目配置
    config = get_project_config(base_path)
    code_root = config.get_package_dir(base_path)
    import_prefix = config.get_import_prefix()

    # 尝试从已生成的模型文件中读取基类信息
    base_class = _get_base_class_from_model_file(code_root, _to_snake_case(name))
    model = ModelDefinition(name=name, base_class=base_class)

    content = _generate_api_content(model, import_prefix)
    file_path = code_root / "api" / f"{model.file_name}.py"
    rel_path = file_path.relative_to(base_path)

    if _create_file(file_path, content, force):
        console.print(f"[green]✅ 创建 API: {rel_path}[/green]")
        
        # 自动注册到 api/__init__.py
        if not no_register:
            if _register_router_in_api_init(code_root, model):
                console.print("[green]✅ 已自动注册到 api/__init__.py[/green]")
            else:
                console.print("[dim]提示: 请在 api/__init__.py 中注册路由:[/dim]")
                console.print(f"[dim]  from . import {model.file_name}[/dim]")
                console.print(f"[dim]  router.include_router({model.file_name}.router)[/dim]")
    else:
        console.print("[yellow]⚠️  文件已存在（使用 --force 覆盖）[/yellow]")


@app.command(name="schema")
def generate_schema(
    name: str = typer.Argument(..., help="模型名称"),
    fields: Annotated[
        list[str] | None,
        typer.Argument(help="字段定义"),
    ] = None,
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="交互式添加字段"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖"),
) -> None:
    """生成 Pydantic Schema。

    示例：
        aury generate schema user
        aury generate schema user email:str:unique age:int?
    """
    base_path = Path.cwd()

    # 读取项目配置
    config = get_project_config(base_path)
    code_root = config.get_package_dir(base_path)

    field_defs: list[FieldDefinition] = []
    if interactive:
        field_defs = _collect_fields_interactive()
    elif fields:
        field_defs = [FieldDefinition.parse(spec) for spec in fields]

    # 尝试从已生成的模型文件中读取基类信息
    base_class = _get_base_class_from_model_file(code_root, _to_snake_case(name))
    model = ModelDefinition(name=name, fields=field_defs, base_class=base_class)

    content = _generate_schema_content(model)
    file_path = code_root / "schemas" / f"{model.file_name}.py"
    rel_path = file_path.relative_to(base_path)

    if _create_file(file_path, content, force):
        console.print(f"[green]✅ 创建 Schema: {rel_path}[/green]")
        _update_init_file(
            code_root / "schemas" / "__init__.py",
            f"from .{model.file_name} import {model.class_name}Create, {model.class_name}Response, {model.class_name}Update",
            f"{model.class_name}Create",
        )
    else:
        console.print("[yellow]⚠️  文件已存在（使用 --force 覆盖）[/yellow]")


@app.command(name="crud")
def generate_crud(
    name: str = typer.Argument(..., help="模型名称"),
    fields: Annotated[
        list[str] | None,
        typer.Argument(help="字段定义"),
    ] = None,
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="交互式添加字段"
    ),
    base: str | None = typer.Option(
        None, "--base", "-b",
        help="模型基类（Model/UUIDModel/UUIDAuditableStateModel/VersionedModel 等）"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖"),
    no_soft_delete: bool = typer.Option(False, "--no-soft-delete", help="禁用软删除"),
    no_timestamps: bool = typer.Option(False, "--no-timestamps", help="禁用时间戳"),
) -> None:
    """一键生成完整 CRUD（model + repo + service + api + schema）。

    支持两种模式：

    1. 命令行参数（AI 友好）:
        aury generate crud user email:str:unique age:int? status:str=active

    2. 交互式（人类友好）:
        aury generate crud user -i

    示例：
        aury generate crud user
        aury generate crud user --base Model  # 使用 int 主键
        aury generate crud user --base UUIDAuditableStateModel  # 使用 UUID 主键（推荐）
        aury generate crud user email:str:unique age:int? --force
        aury generate crud article title:str(200) content:text status:str=draft
    """
    base_path = Path.cwd()
    
    # 读取项目配置
    config = get_project_config(base_path)
    code_root = config.get_package_dir(base_path)
    
    # 解析字段和基类
    field_defs: list[FieldDefinition] = []
    selected_base_class: str | None = base

    if interactive:
        # 交互式模式：先选择基类，再添加字段
        selected_base_class = _collect_base_class_interactive()
        field_defs = _collect_fields_interactive()
    elif fields:
        for spec in fields:
            try:
                field_defs.append(FieldDefinition.parse(spec))
            except Exception as e:
                console.print(f"[red]❌ 解析字段失败: {spec} - {e}[/red]")
                raise typer.Exit(1) from e

    # 验证基类名称
    if selected_base_class and selected_base_class not in MODEL_BASE_CLASSES:
        console.print(f"[red]❌ 无效的基类: {selected_base_class}[/red]")
        console.print(f"[dim]可用基类: {', '.join(MODEL_BASE_CLASSES.keys())}[/dim]")
        raise typer.Exit(1)

    model = ModelDefinition(
        name=name,
        fields=field_defs,
        soft_delete=not no_soft_delete,
        timestamps=not no_timestamps,
        base_class=selected_base_class,
    )

    console.print(
        Panel.fit(
            f"[bold cyan]⚡ 生成 CRUD: {model.class_name}[/bold cyan]",
            border_style="cyan",
        )
    )

    # 显示字段信息
    if model.fields:
        console.print("\n[bold]字段列表:[/bold]")
        for f in model.fields:
            modifiers = []
            if f.nullable:
                modifiers.append("nullable")
            if f.unique:
                modifiers.append("unique")
            if f.index:
                modifiers.append("index")
            if f.default:
                modifiers.append(f"default={f.default}")
            mod_str = f" [{', '.join(modifiers)}]" if modifiers else ""
            console.print(f"  • {f.name}: {f.type_name}{mod_str}")

    console.print()

    # 获取 import_prefix（项目配置已在前面读取）
    import_prefix = config.get_import_prefix()

    # 生成所有文件，直接使用已创建的 ModelDefinition 对象，确保基类信息一致
    # 1. 生成 Model
    model_content = _generate_model_content(model)
    model_file_path = code_root / "models" / f"{model.file_name}.py"
    model_rel_path = model_file_path.relative_to(base_path)
    if _create_file(model_file_path, model_content, force):
        console.print(f"[green]✅ 创建模型: {model_rel_path}[/green]")
        _update_init_file(
            code_root / "models" / "__init__.py",
            f"from .{model.file_name} import {model.class_name}",
            model.class_name,
        )
    else:
        console.print(f"[yellow]⚠️  文件已存在: {model_rel_path}（使用 --force 覆盖）[/yellow]")

    # 2. 生成 Repository
    repo_content = _generate_repository_content(model, import_prefix)
    repo_file_path = code_root / "repositories" / f"{model.file_name}_repository.py"
    repo_rel_path = repo_file_path.relative_to(base_path)
    if _create_file(repo_file_path, repo_content, force):
        console.print(f"[green]✅ 创建仓储: {repo_rel_path}[/green]")
        _update_init_file(
            code_root / "repositories" / "__init__.py",
            f"from .{model.file_name}_repository import {model.class_name}Repository",
            f"{model.class_name}Repository",
        )
    else:
        console.print(f"[yellow]⚠️  文件已存在: {repo_rel_path}（使用 --force 覆盖）[/yellow]")

    # 3. 生成 Service
    service_content = _generate_service_content(model, import_prefix)
    service_file_path = code_root / "services" / f"{model.file_name}_service.py"
    service_rel_path = service_file_path.relative_to(base_path)
    if _create_file(service_file_path, service_content, force):
        console.print(f"[green]✅ 创建服务: {service_rel_path}[/green]")
        _update_init_file(
            code_root / "services" / "__init__.py",
            f"from .{model.file_name}_service import {model.class_name}Service",
            f"{model.class_name}Service",
        )
    else:
        console.print(f"[yellow]⚠️  文件已存在: {service_rel_path}（使用 --force 覆盖）[/yellow]")

    # 4. 生成 Schema
    schema_content = _generate_schema_content(model)
    schema_file_path = code_root / "schemas" / f"{model.file_name}.py"
    schema_rel_path = schema_file_path.relative_to(base_path)
    if _create_file(schema_file_path, schema_content, force):
        console.print(f"[green]✅ 创建 Schema: {schema_rel_path}[/green]")
        _update_init_file(
            code_root / "schemas" / "__init__.py",
            f"from .{model.file_name} import {model.class_name}Create, {model.class_name}Response, {model.class_name}Update",
            f"{model.class_name}Create",
        )
    else:
        console.print(f"[yellow]⚠️  文件已存在: {schema_rel_path}（使用 --force 覆盖）[/yellow]")

    # 5. 生成 API
    api_content = _generate_api_content(model, import_prefix)
    api_file_path = code_root / "api" / f"{model.file_name}.py"
    api_rel_path = api_file_path.relative_to(base_path)
    if _create_file(api_file_path, api_content, force):
        console.print(f"[green]✅ 创建 API: {api_rel_path}[/green]")
        # 自动注册到 api/__init__.py
        if _register_router_in_api_init(code_root, model):
            console.print("[green]✅ 已自动注册到 api/__init__.py[/green]")
        else:
            console.print("[dim]提示: 请在 api/__init__.py 中注册路由:[/dim]")
            console.print(f"[dim]  from . import {model.file_name}[/dim]")
            console.print(f"[dim]  router.include_router({model.file_name}.router)[/dim]")
    else:
        console.print(f"[yellow]⚠️  文件已存在: {api_rel_path}（使用 --force 覆盖）[/yellow]")

    console.print()
    console.print("[bold green]✨ CRUD 生成完成！[/bold green]")
    console.print()
    console.print("[bold]下一步：[/bold]")
    console.print("  1. 生成数据库迁移：")
    console.print(f'     [cyan]aury migrate make -m "add {model.file_name} table"[/cyan]')
    console.print("  2. 执行迁移：")
    console.print("     [cyan]aury migrate up[/cyan]")


__all__ = ["app"]
