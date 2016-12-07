"""HaloEvent connector settings"""

#!/usr/bin/python
# -*- coding: utf-8 -*-


def per_page():
    """max events return per page"""
    return 100

def pagination_limit():
    """max page return"""
    return 50

def historical_limit():
    """max days"""

    return 90

def threads():
    """max parallel threads"""
    return 5
