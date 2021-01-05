#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Collect Information about branches sufficient to check for all branch
protection guideline compliance."""

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# Todo figure out how to avoid global
_collection_date: str = "1970-01-01"

# Collect and return information about organization protections
class OrgData:
    def __init__(
        self: Any,
        *,
        login: str,
        org_name: str = "",
        requires_two_factor_authentication: bool = False,
        org_v4id: Optional[str] = None,
        org_v3id: Optional[str] = None,
        data_source: Any = None,
    ) -> None:
        super().__init__()

        self.login: str = login
        self.org_name: str = org_name
        self.requires_two_factor_authentication: bool = requires_two_factor_authentication
        self.org_v4id: Optional[str] = org_v4id
        self.org_v3id: Optional[str] = org_v3id
        self._type: str = "OrgInfo"
        self._revision: int = 1
        self._data_source = data_source

    @staticmethod
    def metadata_to_log() -> List[str]:
        return ["org_name", "login", "requires_two_factor_authentication", "org_v4id"]

    @staticmethod
    def idfn(val: Any) -> Optional[str]:
        """provide ID for pytest Parametrization."""
        if isinstance(val, (OrgData,)):
            return f"{val.login}"
        return None

    def as_dict(self):
        global _collection_date
        d = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        d["day"] = _collection_date
        return d

    def queryService(self: Any) -> None:
        """
        queryService Fill in data by querying GitHub

        We collect all possibly needed data at this point. There should be no need for service access after this.

        Args:
            endpoint (str): GraphQL session to use

        Returns:
            None: side effect of fields in this object created & updated
        """
        query = (
            self._data_source()
        )  # TODO: this needs to be replaced by a class function returning an object of our class
        query.retrieve_org_data(self)
        query.extract_org_data(self)

        pass

    # Update methods to be called by the query code.
    # as we query the key, we'll obtain immutable id's for the objects that map
    # to those names at this moment in time. It's the query code's
    # responsibility to call this method.
    def update_with_github_info(
        self: Any,
        org_name,
        login,
        requires_two_factor_authentication,
        org_v4id,
        org_v3id,
    ) -> None:
        """
        update_with_github_info sets the GitHub specific information

        Names for GitHub objects are mutable, and we have seen both
        organizations and repositories renamed. To avoid ambiguity and make
        tracing practical, we record the id's as we find them.

        Note that a missing mapping can mean either that there is no longer
        such an object with that name, or that we do not have permissions to
        query that object.

        Args:
            org_name=orgdata.name,
            login=orgdata.login,
            requires_two_factor_authentication=orgdata.requires_two_factor_authentication,
            org_v4id=orgdata.id,
            org_v3id=orgdata.database_id,) -> None:
        """
        self.org_name = org_name
        self.login = login
        self.requires_two_factor_authentication = requires_two_factor_authentication
        self.org_v4id = org_v4id
        self.org_v3id = org_v3id
