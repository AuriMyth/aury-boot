"""{class_name} 数据模型。"""

from sqlalchemy import {imports_str}
from sqlalchemy.orm import Mapped, mapped_column

from aury.boot.domain.models import {base_class}


class {class_name}({base_class}):
    """{class_name} 模型。

    {base_doc}
    """

    __tablename__ = "{table_name}"

{fields_str}
