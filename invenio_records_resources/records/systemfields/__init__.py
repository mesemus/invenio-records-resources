# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
# Copyright (C) 2020 Northwestern University.
#
# Invenio-Records-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""System fields for records."""

from .index import IndexField
from .pid import PIDField
from .pid_statuscheck import PIDStatusCheckField

__all__ = (
    'IndexField',
    'PIDField',
    'PIDStatusCheckField',
)