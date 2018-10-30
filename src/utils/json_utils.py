#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cgi
import json

def _ListToTHMLInternal(in_value, indent=""):
    retHTML = ""
    if issubclass(type(in_value), list) or issubclass(type(in_value), tuple):
        for value in in_value:
            if issubclass(type(value), dict):
                retHTML += "{}    <TD>{}</TD>\n".format(indent, DicToTHML(value))
            elif issubclass(type(value), list) or issubclass(type(value), tuple):
                retHTML += "{}    <TD>{}</TD>\n".format(indent, ListToTHML(value))
            else:
                retHTML += "{}    <TD>{}</TD>\n".format(indent, cgi.escape(str(value)))
    return retHTML

def ListToTHML(in_list, indent=""):
    retHTML = "{}<TABLE>\n".format(indent)
    for value in in_list:
        retHTML += "{}  <TR>\n".format(indent)
        if issubclass(type(value), dict):
            retHTML += "{}    <TD>{}</TD>\n".format(indent, DicToTHML(value))
        elif issubclass(type(value), list) or issubclass(type(value), tuple):
            retHTML += _ListToTHMLInternal(value, indent + "  ")
        else:
            retHTML += "{}    <TD>{}</TD>\n".format(indent, cgi.escape(str(value)))
        retHTML += "{}  </TR>\n".format(indent)
    retHTML += "{}</TABLE>\n".format(indent)
    return retHTML

def DicToTHML(in_dic, indent="", sort_results=False):
    retHTML = "{}<TABLE>\n".format(indent)
    keys = sorted(in_dic.keys()) if sort_results else in_dic.keys()
    for key in keys:
        value = in_dic[key]
        if key.startswith('_'):
            continue
        retHTML += "{}  <TR>\n".format(indent)
        retHTML += "{}    <TD>{}</TD>\n".format(indent, key)
        if issubclass(type(value), dict):
            retHTML += "{}    <TD>{}</TD>\n".format(indent, DicToTHML(value, indent + "  "))
        elif issubclass(type(value), list) or issubclass(type(value), tuple):
            retHTML += "{}    <TD>{}</TD>\n".format(indent, ListToTHML(value, indent + "  "))
        else:
            retHTML += "{}    <TD>{}</TD>\n".format(indent, cgi.escape(str(value)))
        retHTML += "{}  </TR>\n".format(indent)
    retHTML += "{}</TABLE>\n".format(indent)
    return retHTML
