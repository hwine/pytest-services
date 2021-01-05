#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Collect Information about branches sufficient to check for all branch
protection guideline compliance."""

import logging
import os
from pathlib import Path
import subprocess  # nosec
from typing import Iterator, List, Set

from sgqlc.operation import Operation

from github import github_schema as schema
from github import sgqlc_session

from .helpers import OrgData

logger = logging.getLogger(__name__)


class OrgQuery(sgqlc_session.SGQLCGitHubHelper):
    def create_operation(self, owner):
        """Create the default Query operation.

        We build the structure for:
        organization:
            org_name (may contain spaces)
            login (no spaces)
            requires 2fa
        """

        op = Operation(schema.Query)

        org = op.organization(login=owner)
        org.name()
        org.login()
        org.requires_two_factor_authentication()
        org.id()
        org.database_id()

        return op

    def retrieve_org_data(self, org_data: OrgData) -> None:
        op = self.create_operation(org_data.login)
        logger.info("Downloading base information from %s", self._api_session)

        d = self._api_session(op)
        errors = d.get("errors")
        if errors:
            self._report_download_errors(errors)

        orgdata = (op + d).organization
        self.orgdata = orgdata

        logger.info("Finished downloading organization: %s", org_data.login)
        logger.debug("%s", orgdata)
        return

    def extract_org_data(self, org: OrgData) -> None:
        """extract relevant data from sgqlc structure."""
        orgdata = self.orgdata
        org.update_with_github_info(
            org_name=orgdata.name,
            login=orgdata.login,
            requires_two_factor_authentication=orgdata.requires_two_factor_authentication,
            org_v4id=orgdata.id,
            org_v3id=orgdata.database_id,
        )
        return

    ## TODO: Move into base class
    def validate_viewer(self, endpoint):
        # Debugging proper credentials can be challenging, so print out the
        # "viewer" ("authenticated user" in v3 parlance)

        from sgqlc.operation import Operation  # noqa: I900
        from github import github_schema as schema  # noqa: I900

        op = Operation(schema.Query)

        org = op.viewer()
        org.login()
        d = endpoint(op)
        errors = d.get("errors")
        if errors:
            raise ValueError("Invalid GitHub credentials")


## TODO: move into "pytest" class
def _in_offline_mode() -> bool:
    is_offline = False
    try:
        # if we're running under pytest, we need to fetch the value from
        # the current configuration
        import conftest

        is_offline = conftest.get_client("github_client").is_offline()
        if not is_offline:
            # check for a valid GH_TOKEN here so we fail during test collection
            os.environ["GH_TOKEN"]
            # endpoint = get_connection(
            #     DEFAULT_GRAPHQL_ENDPOINT, os.environ.get("GH_TOKEN")
            # )
            # validate_viewer(endpoint)

    except ImportError:
        pass

    return is_offline


def _orgs_to_check() -> Set[str]:
    # just shell out for now
    #   While there is no network operation done here, we don't want to go
    #   poking around the file system if we're in "--offline" mode
    #   (aka doctest mode)
    if OrgQuery.in_offline_mode(auto_login=True):
        return set()
    # DEV_HACK: find better way to insert dev default
    path_to_metadata = os.environ.get(
        "PATH_TO_METADATA", "~/repos/foxsec/master/services/metadata"
    )
    meta_dir = Path(os.path.expanduser(path_to_metadata)).resolve()
    in_files = list(meta_dir.glob("*.json"))

    cmd = [
        "jq",
        "-rc",
        """.codeRepositories[]
                | select(.status == "active")
                | [.url]
                | @csv
                """,
        *in_files,
    ]
    # python 3.6 doesn't support capture_output
    status = subprocess.run(cmd, capture_output=True)  # nosec
    assert not status.stderr.decode("utf-8")
    # return as array of non-empty, unquoted, "lines"
    return {
        x.split("/")[3].translate({ord('"'): None, ord("'"): None})
        for x in status.stdout.decode("utf-8").split("\n")
        if x
    }


## TODO decide later on if this is a supported use case
##      it likely is, but need to enable frost option for it then. Until
##      then, the parameter defaults to False, so will work for automation
## def _all_owned_orgs(endpoint: Any) -> List[str]:
##     """Return a list of all orgs for which this user has owner permissions."""
##
##     op = Operation(schema.Query)
##
##     me = op.viewer()
##     me.login()
##     org = me.organizations(first=100).nodes()
##     org.login()
##     org.viewer_can_administer()
##     d = endpoint(op)
##     errors = d.get("errors")
##     if errors:
##         endpoint.report_download_errors(errors)
##         raise StopIteration
##     else:
##         for x in (op + d).viewer.organizations.nodes:
##             if x.viewer_can_administer:
##                 yield x.login


def get_all_org_data(
    specified_orgs: List[str] = None, all_permitted: bool = False
) -> Iterator[OrgData]:
    """Generator of org data."""
    orgs = set()
    if not specified_orgs:
        if all_permitted:
            # TODO comming back soon, see above
            # orgs = _all_owned_orgs(endpoint)
            pass
        else:
            # Just get the ones we are configured to monitor
            orgs = _orgs_to_check()
    for i, login in enumerate(orgs):
        org_data = OrgData(login=login, data_source=OrgQuery)
        org_data.queryService()
        yield org_data
        # DEVHACK
        # if i > 5: break


if __name__ == "__main__":
    pass
