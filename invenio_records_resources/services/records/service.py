# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
# Copyright (C) 2020 Northwestern University.
#
# Invenio-Records-Resources is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Record Service API."""

from invenio_db import db
from invenio_records_permissions.api import permission_filter
from invenio_search import current_search_client

from ...config import lt_es7
from ..base import Service
from .config import RecordServiceConfig
from .schema import MarshmallowServiceSchema


class RecordService(Service):
    """Record Service."""

    default_config = RecordServiceConfig

    #
    # Low-level API
    #
    @property
    def indexer(self):
        """Factory for creating an indexer instance."""
        return self.config.indexer_cls(
            record_cls=self.config.record_cls,
            record_to_index=self.record_to_index,
        )

    def record_to_index(self, record):
        """Function used to map a record to an index."""
        # We are returning "_doc" as document type as recommended by
        # Elasticsearch documentation to have v6.x and v7.x equivalent. In v8
        # document types will have been completely removed.
        return record.index._name, '_doc'

    @property
    def schema(self):
        """Returns the data schema instance."""
        return MarshmallowServiceSchema(self, schema=self.config.schema)

    @property
    def schema_search_links(self):
        """Returns the schema used for making search links."""
        return MarshmallowServiceSchema(
            self, schema=self.config.schema_search_links)

    @property
    def components(self):
        """Return initialized service components."""
        return (c(self) for c in self.config.components)

    @property
    def record_cls(self):
        """Factory for creating a record class."""
        return self.config.record_cls

    def create_search(self, identity, record_cls, action='read',
                      preference=True):
        """Instantiate a search class."""
        permission = self.permission_policy(
            action_name=action, identity=identity)

        search = self.config.search_cls(
            using=current_search_client,
            default_filter=permission_filter(permission=permission),
            index=record_cls.index.search_alias,
        )

        # Avoid query bounce problem
        if preference:
            search = search.with_preference_param()

        # Add document version to ES response
        search = search.params(version=True)

        # Extras
        extras = {}
        if not lt_es7:
            extras["track_total_hits"] = True
        search = search.extra(**extras)

        return search

    def search_request(self, identity, params, record_cls, preference=True):
        """Factory for creating a Search DSL instance."""
        search = self.create_search(
            identity,
            record_cls,
            preference=preference,
        )

        # Run search args evaluator
        for interpreter_cls in self.config.search_params_interpreters_cls:
            search = interpreter_cls(self.config).apply(
                identity, search, params
            )

        return search

    #
    # High-level API
    #
    def search(self, identity, params=None, links_config=None, **kwargs):
        """Search for records matching the querystring."""
        # Permissions
        self.require_permission(identity, "search")

        # Merge params
        # NOTE: We allow using both the params variable, as well as kwargs. The
        # params is used by the resource, and kwargs is used to have an easier
        # programatic interface .search(idty, q='...') instead of
        # .search(idty, params={'q': '...'}).
        params = params or {}
        params.update(kwargs)

        # Create a Elasticsearch DSL
        search = self.search_request(
            identity, params, self.record_cls, preference=False)

        # Run components
        for component in self.components:
            if hasattr(component, 'search'):
                search = component.search(identity, search, params)

        # Execute the search
        search_result = search.execute()

        return self.result_list(
            self,
            identity,
            search_result,
            params,
            links_config=links_config
        )

    def create(self, identity, data, links_config=None):
        """Create a record.

        :param identity: Identity of user creating the record.
        :param data: Input data according to the data schema.
        """
        return self._create(
            self.record_cls, identity, data, links_config=links_config)

    def _create(self, record_cls, identity, data, links_config=None):
        """Create a record.

        :param identity: Identity of user creating the record.
        :param data: Input data according to the data schema.
        """
        self.require_permission(identity, "create")

        # Validate data and create record with pid
        data, _ = self.schema.load(identity, data)
        # It's the components who saves the actual data in the record.
        record = record_cls.create({})

        # Run components
        for component in self.components:
            if hasattr(component, 'create'):
                component.create(identity, data=data, record=record)

        # Persist record (DB and index)
        record.commit()
        db.session.commit()
        if self.indexer:
            self.indexer.index(record)

        return self.result_item(
            self,
            identity,
            record,
            links_config=links_config
        )

    def read(self, id_, identity, links_config=None):
        """Retrieve a record."""
        # Resolve and require permission
        # TODO must handle delete records and tombstone pages
        record = self.record_cls.pid.resolve(id_)
        self.require_permission(identity, "read", record=record)

        # Run components
        for component in self.components:
            if hasattr(component, 'read'):
                component.read(identity, record=record)

        return self.result_item(
            self,
            identity,
            record,
            links_config=links_config
        )

    def update(self, id_, identity, data, links_config=None):
        """Replace a record."""
        # TODO: etag and versioning
        record = self.record_cls.pid.resolve(id_)

        # Permissions
        self.require_permission(identity, "update", record=record)
        data, _ = self.schema.load(
            identity, data, pid=record.pid, record=record)

        # Run components
        for component in self.components:
            if hasattr(component, 'update'):
                component.update(identity, data=data, record=record)

        # TODO: remove next two lines.
        record.update(data)
        record.clear_none()
        record.commit()
        db.session.commit()

        if self.indexer:
            self.indexer.index(record)

        return self.result_item(
            self,
            identity,
            record,
            links_config=links_config
        )

    def delete(self, id_, identity):
        """Delete a record from database and search indexes."""
        # TODO: etag and versioning
        record = self.record_cls.pid.resolve(id_)

        # Permissions
        self.require_permission(identity, "delete", record=record)

        # Run components
        for component in self.components:
            if hasattr(component, 'delete'):
                component.delete(identity, record=record)

        record.delete()
        db.session.commit()

        if self.indexer:
            self.indexer.delete(record)

        return True