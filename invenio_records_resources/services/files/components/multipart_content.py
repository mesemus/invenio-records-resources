# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 CERN.
#
# Invenio-Records-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Files service components."""
from werkzeug.exceptions import NotFound

from ...errors import FailedFileUploadException, TransferException
from ..transfer import Transfer
from .base import FileServiceComponent


class FileMultipartContentComponent(FileServiceComponent):
    """File metadata service component."""

    def set_file_multipart_content(self, identity, id, file_key, part,
                                   stream, content_length, record):
        """Set file content handler."""
        # Check if associated file record exists and is not already committed.
        file_record = record.files.get(file_key)
        if file_record is None:
            raise NotFound(f'File with key "{file_key}" has not been initialized yet.')

        file_type = file_record.file.storage_class if file_record.file else None
        transfer = Transfer.get_transfer(file_type)
        try:
            transfer.set_file_multipart_content(
                record, file_record.file, file_key, part, stream, content_length
            )
        except TransferException as e:
            raise FailedFileUploadException(
                file_key=file_key, recid=record.pid, file=file_record
            )
