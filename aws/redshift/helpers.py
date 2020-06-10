def redshift_cluster_security_group_test_id(security_group):
    return security_group["ClusterSecurityGroupName"]


def redshift_cluster_security_group_is_open_to_all_ips(security_group):
    """
    Returns True if the security group grants access to all IPs.

    Does not check EC2 Security groups.


    >>> redshift_cluster_security_group_is_open_to_all_ips({'IPRanges': [{'CIDRIP': '0.0.0.0/0'}]})
    True
    >>> redshift_cluster_security_group_is_open_to_all_ips({'IPRanges': [{'CIDRIP': '::/0'}]})
    True

    >>> redshift_cluster_security_group_is_open_to_all_ips({'IPRanges': [{'CIDRIP': '192.168.1.1'}]})
    False
    >>> redshift_cluster_security_group_is_open_to_all_ips({'IPRanges': []})
    False
    >>> redshift_cluster_security_group_is_open_to_all_ips({})
    False

    """
    return any(
        ipr.get("CIDRIP", None) in ["0.0.0.0/0", "::/0"]
        for ipr in security_group.get("IPRanges", [])
    )
