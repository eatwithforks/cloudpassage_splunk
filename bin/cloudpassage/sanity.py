"""Collection of functions for doing validation and sanity checking"""

import re
from cloudpassage.exceptions import CloudPassageValidation


def validate_servergroup_create(server_group_attributes):
    """Validate ServerGroup creation arguments"""

    val_struct = {
        "firewall_policy_id": unicode,
        "linux_firewall_policy_id": unicode,
        "windows_firewall_policy_id": unicode,
        "policy_ids": list,
        "windows_policy_ids": list,
        "fim_policy_ids": list,
        "linux_fim_policy_ids": list,
        "windows_fim_policy_ids": list,
        "lids_policy_ids": list,
        "tag": unicode,
        "server_events_policy": unicode,
        "alert_profiles": list,
        "parent_id": unicode
    }

    for k, value in server_group_attributes.items():
        if k in val_struct:
            if isinstance(value, val_struct[k]):
                continue
            else:
                raise TypeError("Type incorrect for %s.  Is %s.  Should be %s."
                                % (k, type(value), val_struct[k]))
        else:
            raise KeyError("Invalid server group attribute: %s") % k
    return True


def validate_servergroup_update(server_group_attributes):
    """Validate ServerGroup update arguments"""

    val_struct = {
        "firewall_policy_id": str,
        "linux_firewall_policy_id": str,
        "windows_firewall_policy_id": str,
        "policy_ids": list,
        "windows_policy_ids": list,
        "fim_policy_ids": list,
        "linux_fim_policy_ids": list,
        "windows_fim_policy_ids": list,
        "lids_policy_ids": list,
        "tag": str,
        "name": str,
        "special_events_policy": str,
        "alert_profiles": list,
        "parent_id": str
    }

    for k, value in server_group_attributes.items():
        if k in val_struct:
            if isinstance(value, val_struct[k]):
                continue
            elif (val_struct[k] == str) and (value is None):
                continue
            elif (val_struct[k] == str) and (isinstance(value, unicode)):
                continue
            else:
                print "Failed to match"
                raise TypeError("Type incorrect for %s.  Is %s.  Should be %s."
                                % (k, type(value), val_struct[k]))
        else:
            raise KeyError("Invalid server group attribute: %s") % k
    return True


def validate_object_id(object_id):
    """Validates object ID (server_id, policy_id, etc...)

    This function validates Object IDs with the intent of guarding against \
    URL traversal.

    Args:
        object_id (str or list): Object ID to be validated

    Returns:
        (bool) True if valid, throws an exception otherwise.

    """

    rex = re.compile('^[A-Za-z0-9]+$')
    if isinstance(object_id, (str, unicode)):
        if not rex.match(object_id):
            error_message = "Object ID failed validation: %s" % object_id
            raise CloudPassageValidation(error_message)
        else:
            return True
    elif isinstance(object_id, list):
        for individual in object_id:
            if not rex.match(individual):
                error_message = "Object ID failed validation: %s" % object_id
                raise CloudPassageValidation(error_message)
        return True
    else:
        error_message = "Wrong type for object ID: %s" % str(type(object_id))
        raise TypeError(error_message)


def validate_api_hostname(api_hostname):
    """Validate hostname for API endpoint"""
    hostname_is_valid = False
    valid_api_host = re.compile(r'^([A-Za-z0-9-]+\.){1,2}cloudpassage\.com$')
    if valid_api_host.match(api_hostname):
        hostname_is_valid = True
    return hostname_is_valid
