# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Collect Information about branches sufficient to check for all branch
protection guideline compliance."""
# TODO add doctests

from datetime import date
import logging
import os
from typing import Any, Optional

from sgqlc.endpoint.http import HTTPEndpoint  # noqa: I900

DEFAULT_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
EXTENSION_TO_STRIP = ".git"

logger = logging.getLogger(__name__)


class SGQLCGitHubHelper:

    # class vars
    _collection_date: str = "1970-01-01"
    _api_session: Optional[HTTPEndpoint] = None

    # helper classes for graph errors
    @classmethod
    def _compact_fmt(cls, d: dict):
        s = []
        for k, v in d.items():
            if isinstance(v, dict):
                v = cls._compact_fmt(v)
            elif isinstance(v, (list, tuple)):
                lst = []
                for e in v:
                    if isinstance(e, dict):
                        lst.append(cls._compact_fmt(e))
                    else:
                        lst.append(repr(e))
                s.append("{}=[{}]".format(k, ", ".join(lst)))
                continue
            s.append(f"{k}={v!r}")
        return "(" + ", ".join(s) + ")"

    @classmethod
    def _report_download_errors(cls, errors: list):
        """error handling for graphql comms."""
        logger.error("Document contain %d errors", len(errors))
        for i, e in enumerate(errors):
            msg = e.pop("message")
            extra = ""
            if e:
                extra = " %s" % cls._compact_fmt(e)
            logger.error("Error #%d: %s%s", i + 1, msg, extra)

    @classmethod
    def get_connection(cls, base_url: str, token: str) -> Any:
        cls._api_session = HTTPEndpoint(base_url, {"Authorization": "bearer " + token,})

        # determine which date we're collecting for
        cls._collection_date == "1970-01-01"
        cls._collection_date = date.today().isoformat()
        return cls._api_session

    @classmethod
    def in_offline_mode(cls, auto_login: bool = False) -> bool:
        is_offline = False
        try:
            # if we're running under pytest, we need to fetch the value from
            # the current configuration
            import conftest

            is_offline = conftest.get_client("github_client").is_offline()
            if not is_offline:
                # check for a valid GH_TOKEN here so we fail during test collection
                os.environ["GH_TOKEN"]
        except ImportError:
            pass

        if not is_offline and not cls._api_session:
            # Go ahead an initialize the connection, but only once
            cls.get_connection(DEFAULT_GRAPHQL_ENDPOINT, os.environ["GH_TOKEN"])
        return is_offline

    @classmethod
    def get_session(cls) -> Any:
        return cls._api_session
