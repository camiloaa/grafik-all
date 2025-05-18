#!/bin/env python3
"""
Test parseql module
"""
# pylint: disable=invalid-name
# pylint: disable=no-member


import os
import yaml
from unittest import TestCase
from grafik_all import parseql


TEST_DIR = os.path.dirname(__file__)


def load_yaml_data(filename: str):
    """ Load yaml data from a file """
    with open(filename, encoding='utf-8') as f:
        json_content = f.read()
    return yaml.safe_load(json_content)


class TestParseql(TestCase):
    """Test GraphQL parser"""

    def test_basic_parse(self):
        """string_to_graphql should create a GraphQLNode"""
        string = 'node(id: "gid://12") { item1 item2 item3 }'
        node, *_ = parseql.string_to_graphql(string)
        self.assertEqual(str(node), string)
        self.assertTrue(all(isinstance(x, parseql.GraphQLNode) for x in node.items()))
        update = parseql.GraphQLNode('', 'sub1', 'sub2')
        node['item1'].update(update)
        self.assertEqual(str(node), 'node(id: "gid://12") { item1 { sub1 sub2 } item2 item3 }')
