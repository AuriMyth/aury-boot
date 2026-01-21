"""{class_name} 数据访问层。"""

from aury.boot.domain.repository.impl import BaseRepository

from {import_prefix}models.{file_name} import {class_name}


class {class_name}Repository(BaseRepository[{class_name}]):
    """{class_name} 仓储。

    继承 BaseRepository 自动获得：
    - get(id): 按 ID 获取
    - get_by(**filters): 按条件获取单个
    - list(skip, limit, sort, **filters): 获取列表
    - paginate(pagination, sort, **filters): 分页获取
    - stream(batch_size, sort, **filters): 流式查询
    - create(data): 创建
    - update(entity, data): 更新
    - delete(entity, soft=True): 删除
    """{methods_str}
