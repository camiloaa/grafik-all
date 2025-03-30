#!/bin/env python3
"""
Test Grafik-all
"""

from unittest import TestCase
from grafik_all import graphql


class TestGraphQL(TestCase):
    """ Unit test for Commit class
    """

    def test_graphql_class_add_method(self):
        """ Test adding items to the node """
        # Items are stored in the order they were added
        basic = graphql.GraphQLNode('project', 'item1', 'item2', _alias='my_project')
        self.assertEqual(str(basic), 'my_project: project { item1 item2 }')
        # Add one more item
        basic.add('item3')
        self.assertEqual(str(basic), 'my_project: project { item1 item2 item3 }')
        # Add a nested graphql node
        basic.add(graphql.GraphQLNode('nested', 'nestedItem'))
        self.assertEqual(str(basic), 'my_project: project { item1 item2 item3 '
                                     'nested { nestedItem } }')

    def test_graphql_add_duplicated(self):
        """ Test adding items to the node """
        # Items are stored in the order they were added
        basic = graphql.GraphQLNode('project', 'item1', 'item1', _alias='my_project')
        self.assertEqual(str(basic), 'my_project: project { item1 }')
        # Add one more item
        basic.add('item3')
        self.assertEqual(str(basic), 'my_project: project { item1 item3 }')
        # Add a nested graphql node
        basic.add(graphql.GraphQLNode('nested', 'nestedItem'))
        self.assertEqual(str(basic), 'my_project: project { item1 item3 '
                                     'nested { nestedItem } }')

    def test_graphql_class_add_params_method(self):
        """ Test adding parameters to the node """
        basic = graphql.GraphQLNode('project', 'item1', name='string')
        self.assertEqual(str(basic), 'project(name: "string") { item1 }')
        # Parameters are stored in the order they were added
        basic.add_params(id='12', integer=4)
        self.assertEqual(str(basic), 'project(name: "string", id: "gid://12",'
                                     ' integer: 4) { item1 }')

    def test_graphql_nodes_wrapper_no_initial_items(self):
        """ Test creating a 'field { nodes { items } }' query """
        nodes_query = graphql.NodesQL('project', id=12)
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes {  } }')
        nodes_query.add_to_nodes('item1', 'item2')
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes { item1 item2 } }')

    def test_graphql_nodes_wrapper_with_initial_items(self):
        """ Test creating a 'field { nodes { items } }' query """
        nodes_query = graphql.NodesQL('project', 'item1', id=12)
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes { item1 } }')
        nodes_query.add_to_nodes('item2')
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes { item1 item2 } }')

    def test_graphql_nodes_wrapper_with_custom_nodes(self):
        """ Test creating a 'field { nodes { items } }' query """
        nodes_items = graphql.GraphQLNode('', 'item1')
        nodes_query = graphql.NodesQL('project', nodes_items, id=12, _nude=True)
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes { item1 } }')
        nodes_query.add_to_nodes('item2')
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes { item1 item2 } }')
        # Internal 'nodes' is a reference to 'nodes_items'
        self.assertEqual(str(nodes_items), '{ item1 item2 }')
        # Duplicated items are removed and added to the end
        nodes_items.add('item1', 'item3')
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes { item2 item1 item3 } }')
