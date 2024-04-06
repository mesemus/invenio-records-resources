# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 CERN.
# Copyright (C) 2020-2021 Northwestern University.
#
# Flask-Resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utility for rendering URI template links."""
from uritemplate import URITemplate

from .transfer import Transfer
from ..base import Link


class FileLink(Link):
    """Short cut for writing record links."""

    @staticmethod
    def vars(file_record, vars):
        """Variables for the URI template."""
        vars.update(
            {
                "key": file_record.key,
            }
        )


class TransferLinks:
    """Links provided by file transfer class."""

    def __init__(self, uritemplate):
        """Initialize the link."""
        self.uritemplate = URITemplate(uritemplate)

    def should_render(self, file_record, ctx):
        """Determine if the link should be rendered."""
        if self._transfer_links(file_record):
            return True
        return False

    def expand(self, file_record, ctx):
        """Determine if the link should be rendered."""
        links = self._transfer_links(file_record)
        if links:
            prefix = self.uritemplate.expand(ctx)
            transfer_ctx = {
                **ctx,
                "prefix": prefix
            }
            return {
                key: transfer_link.expand(file_record, transfer_ctx)
                for key, transfer_link in links.items()
            }
        return {}

    def _transfer_links(self, obj):
        transfer = Transfer.get_transfer(obj.metadata.get('storage_type'))
        if transfer:
            return transfer.links(obj)
        return {}
