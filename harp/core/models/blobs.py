import dataclasses
import hashlib
import json

from harp.utils.bytes import ensure_bytes, ensure_str

from .base import Entity


@dataclasses.dataclass(kw_only=True)
class Blob(Entity):
    id: str
    data: bytes
    content_type: str = None

    @classmethod
    def from_data(cls, data, /, *, content_type=None):
        content_type = ensure_str(content_type) if content_type else None
        if content_type and ";" in content_type:
            # xxx hack, we should parse the rest of the content type
            content_type = content_type.split(";", 1)[0].strip()

        data = ensure_bytes(data)
        return cls(
            id=hashlib.sha1((content_type.encode("utf-8") if content_type else b"") + b"\n" + data).hexdigest(),
            data=data,
            content_type=content_type,
        )

    def __len__(self):
        return len(self.data)

    def __bool__(self):
        return True

    def prettify(self):
        if self.content_type == "application/json":
            return json.dumps(json.loads(self.data), indent=4)

        raise NotImplementedError(f"Cannot prettify blob of type {self.content_type}")
