from __future__ import annotations

import os
import pathlib
import subprocess  # nosec
import logging
from github import sgqlc_session
from sgqlc.operation import Operation  # noqa: I900
from github import github_schema as schema  # noqa: I900
from typing import List, Set
from .helpers import BranchProtectionData, BranchProtectionRule
from .helpers import BranchOfInterest as BranchOfInterest


logger = logging.getLogger(__name__)

EXTENSION_TO_STRIP = ".git"

## # New data structures
##
## # BranchOfInterest comes from Inventory -- immutable & hashable
##
## from collections import namedtuple
## BranchOfInterest = namedtuple("BranchOfInterest", "org_str repo_str branch_str usage_status")
## # These are all values from the inventory (nee metadata) store:
## # org_str -- Name of org, e.g. 'mozilla' or 'mozilla-games'
## # repo_str -- Name of repo, e.g. 'frost' or 'normandy'
## # branch_str -- Name of branch we care about -- may be empty, which means default branch of repo
## # usage_status -- E.g. 'active', 'decomissioned' -- may be empty, which means 'unknown'
##
## @dataclass
## class BranchProtectionRule:
##     """
##      Attributes of a protection rule which apply to this branch
##
##     We invert GitHub's ordering, which has an array of branches each rule matches.
##     We want an array of rules that apply to this branch
##
##     """
##     bpr_v4id: str
##     is_admin_enforced: bool
##     push_actor_count: int
##     rule_conflict_count: int
##     pattern: str
##     _type: str = "BranchProtectionRule"
##     _revision: int = 1
##
##
##     def as_dict(self):
##         return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
##
##


class BranchQuery(sgqlc_session.SGQLCGitHubHelper):
    def _add_protection_fields(self, node) -> None:
        """Build in fields we want to query.

        In normal gQuery, this would be a fragment
        """
        node.__fields__(is_admin_enforced=True, id=True, pattern=True, database_id=True)
        node.branch_protection_rule_conflicts(first=0).__fields__(total_count=True,)
        node.push_allowances(first=0).__fields__(total_count=True,)

    def create_operation(self, owner, name):
        """Create the default Query operation.

        We build the structure for:
        repository:
            0-n branch protections rules
            flags
            0-n conflicts with other rules (we only count)
            0-n actors who can push (we only count)
            0-n branches with this protection
        """

        op = Operation(schema.Query)
        # Here's the query outline we're trying to build and access:
        # query branch_info2($LAST_CURSOR: String, $OWNER: String!, $REPO: String!) {
        #   repository(owner: $OWNER, name: $REPO) {
        #     owner {
        #       id
        #       login
        #     }
        #     name
        #     id
        #     defaultBranchRef {
        #       name
        #     }
        #     branchProtectionRules(first: 10) {
        #       totalCount
        #       pageInfo {
        #         endCursor
        #         hasNextPage
        #       }
        #       nodes {
        #         id
        #         isAdminEnforced
        #         pushAllowances(first: 0) {
        #           totalCount
        #         }
        #         branchProtectionRuleConflicts(first: 0) {
        #           totalCount
        #         }
        #         matchingRefs(first: 2, after: $LAST_CURSOR) {
        #           totalCount
        #           applicable_branches: nodes {
        #             ... on Ref {
        #               name
        #               prefix
        #             }
        #           }
        #         }
        #       }
        #     }
        #   }
        # }

        repo = op.repository(owner=owner, name=name)
        repo.default_branch_ref.__fields__(name=True)
        repo.name_with_owner()
        repo.id()  # v4 id
        repo.database_id()  # v3 id
        repo.owner().id()
        repo.owner().login()

        # now specify which fields we care about
        # we only get one item at a time to
        # simplify getting all.
        # N.B. anything we can get multiple of, we need to gather the 'id'
        #       as well, in case pagination is needed
        branch_protection = repo.branch_protection_rules(first=10)
        branch_protection.total_count()
        branch_protection.page_info.__fields__(end_cursor=True, has_next_page=True)

        # we may have to iterate on branch protection entries
        node = branch_protection.nodes()
        self._add_protection_fields(node)

        # we may have to iterate on matching branches for this branch
        # protection rule
        # Currently, we avoid iteration by tuning the value to never require
        # multiple pages. This technique is brittle, but may be sufficient.
        ref = node.matching_refs(first=50)
        ref.total_count()
        ref.page_info.__fields__(end_cursor=True, has_next_page=True)
        ref.nodes().__fields__(
            name=True,  # string name, like "main"
            prefix=True,  # where the name is stored. usually "refs/heads/"
        )

        return op

    def create_rule_query(self):
        """Create a query object for additional branch protection entries.

        Used to fetch subsequent pages. End Cursor is passed as a variable
        """
        op = Operation(schema.Query)

        node = op.branch_protection_rules.nodes(cursor="$LAST_CURSOR")
        self._add_protection_fields(node)
        return op

    def retrieve_branch_data(self, branch: BranchProtectionData) -> None:
        op = self.create_operation(branch.key.org_str, branch.key.repo_str)

        logger.info("Downloading base information from %s", self._api_session)

        d = self._api_session(op)
        errors = d.get("errors")
        if errors:
            self._report_download_errors(errors)
            return

        repodata = (op + d).repository

        def _more_to_do(cur_result, fake_new_page=False):
            """Determine if we need another query.

            There are two nested repeating elements in the query - if either
            is not yet exhausted, we have to do another query
            """
            # for hacky testing
            if fake_new_page:
                cur_result.branch_protection_rules.nodes[
                    0
                ].matching_refs.page_info.has_next_page = True

            has_more_rules = cur_result.branch_protection_rules.page_info.has_next_page
            has_more_refs = any(
                x.matching_refs.page_info.has_next_page
                for x in cur_result.branch_protection_rules.nodes
            )
            return has_more_rules or has_more_refs

        # DEV_HACK for testing manually, set fake_next_page to True
        fake_next_page = False

        while _more_to_do(repodata, fake_next_page):
            fake_next_page = False
            # Need to work from inside out.
            # and need to iterate over every rule -- KIS & hope for YAGNI
            more_refs = any(
                x.matching_refs.page_info.has_next_page
                for x in repodata.branch_protection_rules.nodes
            )
            if more_refs:
                # pagination isn't implemented yet. Try upping the limits in the
                # query to avoid tripping this error.
                logger.error(
                    f"Pagination needed for matching refs in {branch!s}- not yet implemented"
                )
                break
            elif repodata.branch_protection_rules.page_info.has_next_page:
                # we can't advance here until all matching refs are gathered
                logger.error(
                    f"Pagination needed for branch protection rules in {branch!s}- not yet implemented"
                )
                break
            else:
                logger.error("ERROR: bad logic in pagination tests")

            logger.debug("Operation:\n%s", op)

            cont = self._api_session(op)
            errors = cont.get("errors")
            if errors:
                return self._report_download_errors(errors)

            (op + cont).repository

        logger.info("Finished downloading repository: %s", branch.key)
        logger.debug("%s", repodata)

        self.repodata = repodata

        return

    def extract_branch_data(self, branch: BranchProtectionData) -> None:
        """extract relevant data from sgqlc structure."""
        repodata = self.repodata
        branch.update_with_github_info(
            repodata.owner.id, repodata.id, repodata.default_branch_ref.name
        )
        branch_name = branch.key.branch_str
        if not branch_name:
            # search for rules that apply to the repo's default branch
            branch_name = branch.default_branch
        # Find each rule for this branch
        rules = [
            BranchProtectionRule(
                r.id,
                r.is_admin_enforced,
                r.push_allowances.total_count,
                r.branch_protection_rule_conflicts.total_count,
                r.pattern,
            )
            for r in repodata.branch_protection_rules.nodes
            if branch_name in [n.name for n in r.matching_refs.nodes]
        ]
        branch.update_with_branch_rules(rules)
        return


def repos_to_check() -> List[BranchProtectionData]:
    # just shell out for now
    #   While there is no network operation done here, we don't want to go
    #   poking around the file system if we're in "--offline" mode
    #   (e.g. doctest mode)
    # If we aren't offline, we do want to login -- we can't do that in conftest
    # files due to execution order. (The lower conftest executes first, so
    # "offline" isn't known at time of session setup there.)
    if BranchQuery.in_offline_mode(auto_login=True):
        # if sgqlc_session.SGQLCGitHubHelper.in_offline_mode(auto_login=True):
        return []
    # BranchProtectionData.set_query_method(BranchQuery.get_session())

    # real work
    # DEV_HACK: find better way to insert dev default
    path_to_metadata = os.environ.setdefault(
        "PATH_TO_METADATA", "~/repos/foxsec/master/services/metadata"
    )
    meta_dir = pathlib.Path(os.path.expanduser(path_to_metadata)).resolve()
    in_files = list(meta_dir.glob("*.json"))

    cmd = [
        "jq",
        "-rc",
        """.codeRepositories[]
                | select(.status != "deprecated")
                | .url as $url
                | .status as $status
                | .branchesToProtect[] // ""
                | [$url, ., $status ]
                | @csv
                """,
        *in_files,
    ]

    status = subprocess.run(cmd, capture_output=True)  # nosec
    branches_to_check: Set[BranchOfInterest] = set()
    for line in [
        x.translate({ord('"'): None, ord("'"): None})
        for x in status.stdout.decode("utf-8").split("\n")
        if x
    ]:
        if "," in line:
            url, branch, usage_status = line.split(",")
        else:
            url, branch, usage_status = line, "", "unknown"
        owner, repo = url.split("/")[3:5]
        if repo.endswith(EXTENSION_TO_STRIP):
            repo = repo[: -len(EXTENSION_TO_STRIP)]
        branch_info = BranchOfInterest(owner, repo, branch, usage_status)
        branches_to_check.add(branch_info)

    # Now we sort the list to improve caching hits
    branches_to_query = sorted(branches_to_check)
    # and populate with full data, after we get a connection
    all_data = []
    for i, b_of_i in enumerate(branches_to_query):
        branch_data = BranchProtectionData(b_of_i, BranchQuery)
        branch_data.queryService()
        all_data.append(branch_data)
        # DEVHACK
        # if i > 5: break

    return all_data
