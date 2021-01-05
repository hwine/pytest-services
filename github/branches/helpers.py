from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Optional, List

logger = logging.getLogger(__name__)

EXTENSION_TO_STRIP = ".git"

# New data structures

# BranchOfInterest comes from Inventory -- immutable & hashable

from collections import namedtuple

BranchOfInterest = namedtuple(
    "BranchOfInterest", "org_str repo_str branch_str usage_status"
)
# These are all values from the inventory (nee metadata) store:
# org_str -- Name of org, e.g. 'mozilla' or 'mozilla-games'
# repo_str -- Name of repo, e.g. 'frost' or 'normandy'
# branch_str -- Name of branch we care about -- may be empty, which means default branch of repo
# usage_status -- E.g. 'active', 'decomissioned' -- may be empty, which means 'unknown'


@dataclass
class BranchProtectionRule:
    """
     Attributes of a protection rule which apply to this branch

    We invert GitHub's ordering, which has an array of branches each rule matches.
    We want an array of rules that apply to this branch

    """

    bpr_v4id: str
    is_admin_enforced: bool
    push_actor_count: int
    rule_conflict_count: int
    pattern: str
    _type: str = "BranchProtectionRule"
    _revision: int = 1

    def as_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class BranchProtectionData:
    """
     Branch protections for a specific branch

    Basically a smart data structure. The ``key`` value is unique in the
    domain, so methods to support sorting on it are defined.

    Attributes:
        key (:obj:`BranchOfInterest`): the unique branch for which data is
            collected
        org_id (str): the v4 id from GitHub
        repo_id (str): the v4 id from GitHub
        default_branch (str): the name of the default branch configured for
            this repo. Used when key.branch_str is None
        protections (:obj:`List` of :obj:`BranchProtectionRule`): all branch
            protection objects which apply to this branch
        _data_source(:obj:`Any`): object which has methods to return data

    """

    @classmethod
    def idfn(cls, val: Any) -> Optional[str]:
        string = None
        if isinstance(val, (BranchProtectionData,)):
            string = str(val)
        return string

    @classmethod
    def metadata_to_log(cls):
        return [
            "key",
            "org_id",
            "repo_id",
            "default_branch",
        ]

    def __init__(self: Any, key: BranchOfInterest, data_source: Any) -> None:
        super().__init__()
        self.key = key
        self.protections = []
        self.org_id: str = None
        self.repo_id: str = None
        self.default_branch: str = None
        self._data_source = data_source

    def __str__(self: Any) -> str:
        k = self.key
        branch = k.branch_str or self.default_branch or "<default>"
        return f"{k.org_str}/{k.repo_str}:{branch}"

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
        query.retrieve_branch_data(self)
        query.extract_branch_data(self)

        pass

    # Update methods to be called by the query code.
    # as we query the key, we'll obtain immutable id's for the objects that map
    # to those names at this moment in time. It's the query code's
    # responsibility to call this method.
    def update_with_github_info(
        self: Any, org_id: str, repo_id: str, default_branch: str
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
            org_id (str): GitHub's v4 API id for the organization
            repo_id (str): GitHub's v4 API id for the repository
            default_branch (str): name of default branch configured for repo
        """
        self.org_id = org_id
        self.repo_id = repo_id
        self.default_branch = default_branch

    def update_with_branch_rules(self, rules: List[BranchProtectionRule]) -> None:
        self.protections = rules

    # support for sorting - not certain it's needed anymore
    def __repr__(self) -> str:
        return f"({self.key.org_str}, {self.key.repo_str}, {self.key.branch_str})"

    def __lt__(self: Any, other: BranchProtectionData) -> bool:
        """
        __lt__ Compare two BranchProtectionData objects for ordering

        Uses tuple comparison of each object's key representation, which is
        (conveniently) in the exact order we want to sort by.

        Args:
            other (:obj:`BranchProtectionData`): them

        Returns:
            bool: True if we should xxpreceed them in an ordered list
        """
        return repr(self.key) < repr(other.key)

    def __hash__(self: Any) -> int:
        return self.key.__hash__()
