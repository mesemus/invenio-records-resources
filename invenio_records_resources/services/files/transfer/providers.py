from invenio_files_rest import current_files_rest
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag

from ...errors import TransferException
from ...uow import TaskOp
from ..tasks import fetch_file
from .base import BaseTransfer
from .types import FETCH_TRANSFER_TYPE, LOCAL_TRANSFER_TYPE, MULTIPART_TRANSFER_TYPE


class LocalTransfer(BaseTransfer):
    """Local transfer."""

    transfer_type = LOCAL_TRANSFER_TYPE

    def __init__(self, **kwargs):
        """Constructor."""
        super().__init__(**kwargs)

    def init_file(self, record, file_metadata):
        """Initialize a file."""
        uri = file_metadata.pop("uri", None)
        if uri:
            raise Exception("Cannot set URI for local files.")

        file = record.files.create(key=file_metadata.pop("key"), data=file_metadata)

        return file

    def set_file_content(self, record, file, file_key, stream, content_length):
        """Set file content."""
        if file:
            raise TransferException(f'File with key "{file_key}" is committed.')

        super().set_file_content(record, file, file_key, stream, content_length)


class FetchTransfer(BaseTransfer):
    """Fetch transfer."""

    transfer_type = FETCH_TRANSFER_TYPE

    def __init__(self, **kwargs):
        """Constructor."""
        super().__init__(**kwargs)

    def init_file(self, record, file_metadata):
        """Initialize a file."""
        uri = file_metadata.pop("uri", None)
        if not uri:
            raise Exception("URI is required for fetch files.")

        obj_kwargs = {
            "file": {
                "uri": uri,
                "storage_class": self.transfer_type.type,
                "checksum": file_metadata.pop("checksum", None),
                "size": file_metadata.pop("size", None),
            }
        }

        file_key = file_metadata.pop("key")
        file = record.files.create(
            key=file_key,
            data=file_metadata,
            obj=obj_kwargs,
        )

        self.uow.register(
            TaskOp(
                fetch_file,
                service_id=self.service.id,
                record_id=record.pid.pid_value,
                file_key=file_key,
            )
        )
        return file


class MultipartTransfer(BaseTransfer):
    """Local transfer."""

    transfer_type = MULTIPART_TRANSFER_TYPE

    def __init__(self, **kwargs):
        """Constructor."""
        super().__init__(**kwargs)

    def init_file(self, record, file_metadata):
        """Initialize a file."""
        uri = file_metadata.pop("uri", None)
        if uri:
            raise Exception("Cannot set URI for local files.")
        parts = file_metadata.pop("parts", None)
        part_size = file_metadata.pop("part_size", None)
        size = file_metadata.get("size", None)
        if not parts:
            raise TransferException("Multipart file transfer requires parts.")
        if not size:
            raise TransferException("Multipart file transfer requires size.")

        file = record.files.create(key=file_metadata.pop("key"), data=file_metadata)

        version = ObjectVersion.create(file.bucket, file.key)
        ObjectVersionTag.create(version, "multipart:parts", str(parts))
        ObjectVersionTag.create(version, "multipart:part_size", str(part_size))

        # get the storage backend
        storage = current_files_rest.storage_factory()  # location=version.bucket.location.uri)

        if not hasattr(storage, "initialize_multipart_upload"):
            raise TransferException(f"Storage backend {type(storage)} "
                                    f"does not support multipart upload.")

        storage.initialize_multipart_upload(file, version, parts, size, part_size)

        return file

    def set_file_content(self, record, file, file_key, stream, content_length):
        """Set file content."""
        raise TransferException("Can not set content for multipart file, "
                                "use the parts instead.")

    def set_file_multipart_content(selfself, record, file, file_key, part, stream, content_length):
        raise NotImplementedError("Not implemented yet.")
