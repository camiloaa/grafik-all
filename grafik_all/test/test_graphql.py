#!/bin/env python3
"""
Test graphql module
"""
# pylint: disable=invalid-name


import os
import yaml
from unittest import TestCase
from grafik_all import graphql


TEST_DIR = os.path.dirname(__file__)


def load_yaml_data(filename: str):
    """ Load yaml data from a file """
    with open(filename, encoding='utf-8') as f:
        json_content = f.read()
    return yaml.safe_load(json_content)


@graphql.GraphQLEnum
def CONSTANT():
    """ Text CONSTANT with attributes """
    return {'my_attr': 'MY_ATTR',
            'other': 0}


class TestGraphQL(TestCase):
    """ Unit test for GraphQL
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
        basic.add(id='12', integer=4, enum=CONSTANT, boolean=True)
        self.assertEqual(str(basic), 'project(name: "string", id: "gid://12",'
                                     ' integer: 4, enum: CONSTANT, boolean: true) '
                                     '{ item1 }')

    def test_graphql_nodes_wrapper_no_initial_items(self):
        """ Test creating a 'field { nodes { items } }' query """
        nodes_query = graphql.NodesQL('project', id=12)
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes {  } }')
        nodes_query.add_to_nodes('item1', 'item2')
        self.assertEqual(str(nodes_query), ('project(id: "gid://12") { '
                                            'project_nodes: nodes { item1 item2 } }'))

    def test_graphql_nodes_wrapper_with_initial_items(self):
        """ Test creating a 'field { nodes { items } }' query """
        nodes_query = graphql.NodesQL('project', 'item1', id=12)
        self.assertEqual(str(nodes_query), ('project(id: "gid://12") { '
                                            'project_nodes: nodes { item1 } }'))
        nodes_query.add_to_nodes('item2')
        self.assertEqual(str(nodes_query), ('project(id: "gid://12") { project_nodes: '
                                            'nodes { item1 item2 } }'))

    def test_graphql_nodes_wrapper_with_custom_nodes(self):
        """ Test creating a 'field { nodes { items } }' query """
        nodes_items = graphql.GraphQLNode('', 'item1')
        nodes_query = graphql.NodesQL('project', _node=nodes_items, id=12)
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes { item1 } }')
        nodes_query.add_to_nodes('item2')
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes { item1 item2 } }')
        # Internal 'nodes' is a reference to 'nodes_items'
        self.assertEqual(str(nodes_items), '{ item1 item2 }')
        # Duplicated items are removed and added to the end
        nodes_items.add('item1', 'item3')
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { project_nodes: nodes { item2 item1 item3 } }')
        # Add extra parameters
        nodes_query.add(name='name')
        self.assertEqual(str(nodes_query), 'project(id: "gid://12", name: "name") '
                                           '{ project_nodes: nodes { item2 item1 item3 } }')

    def test_graphql_nodes_wrapper_with_custom_named_nodes(self):
        """ Test creating a 'field { nodes { items } }' query """
        nodes_items = graphql.GraphQLNode('noName', 'item1')
        nodes_query = graphql.NodesQL('project', _node=nodes_items, id=12)
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { noName: nodes { item1 } }')
        nodes_query.add_to_nodes('item2')
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { noName: nodes { item1 item2 } }')
        # Internal 'nodes' is a reference to 'nodes_items'
        self.assertEqual(str(nodes_items), 'noName { item1 item2 }')
        # Duplicated items are removed and added to the end
        nodes_items.add('item1', 'item3')
        self.assertEqual(str(nodes_query), 'project(id: "gid://12") { noName: nodes { item2 item1 item3 } }')
        # Add extra parameters
        nodes_query.add(name='name')
        self.assertEqual(str(nodes_query), 'project(id: "gid://12", name: "name") '
                                           '{ noName: nodes { item2 item1 item3 } }')

    def test_graphql_pagination_shortcuts(self):
        """ Use pagination shortcuts to change parameters """
        query = graphql.GraphQLNode('project', 'item', first=10, after=0)
        self.assertEqual(str(query), 'project(first: 10, after: 0) { item }')
        # Use a different page
        query.first(5)
        query.after(10)
        self.assertEqual(str(query), 'project(first: 5, after: 10) { item }')
        # Using 'add' has the same result
        query.add(first=7, after=20)
        self.assertEqual(str(query), 'project(first: 7, after: 20) { item }')

    def test_graphql_add_to_all(self):
        """ Add to all adds items to all nodes """
        query = graphql.GraphQLNode('project',
                                    graphql.GraphQLNode('subproject', 'subitem'),
                                    graphql.GraphQLNode('other', 'otheritem'))
        self.assertEqual(str(query), 'project { subproject { subitem } other { otheritem } }')
        # Add an item and parameter to all nodes
        query.add_to_all('new', text='free')
        self.assertEqual(str(query), 'project { '
                                     'subproject(text: "free") { subitem new } '
                                     'other(text: "free") { otheritem new } }')


class TestGraphQLEnums(TestCase):
    """ Unit test for GraphQL Enums
    """

    def test_graphql_enum_is_text(self):
        """ Test that enums behave just like text """
        self.assertEqual(CONSTANT, 'CONSTANT')
        self.assertTrue(CONSTANT in [CONSTANT])
        self.assertTrue(CONSTANT in ['CONSTANT'])
        self.assertTrue('CONSTANT' in [CONSTANT])

    def test_graphql_enum_has_attributes(self):
        """ Test that enums have custom attributes """
        self.assertEqual(CONSTANT.lower, 'constant')
        self.assertEqual(CONSTANT.my_attr, 'MY_ATTR')
        self.assertEqual(CONSTANT.other, 0)

    def test_graphql_enum_does_not_have_quotation_marks(self):
        """ Test that enums do not show quotation marks in GraphQL """
        basic = graphql.GraphQLNode('project', 'item', name=CONSTANT)
        self.assertEqual(str(basic), 'project(name: CONSTANT) { item }')


@graphql.AutoNode(graphql.GraphQLNode)
def TestNode(*_, **__):
    return ('field1', 'field2'), {}


@graphql.AutoNode(graphql.GraphQLNode)
def TestFixedNode(*_, **__):
    """ Fixed items """
    return (('field1', 'field2'),
            {'_valid_items': ['field1', 'field2', 'field3'],
             '_valid_params': ['id', 'and']})


@graphql.AutoNode(graphql.GraphQLNode)
def TestNoItemsNode(*_, **__):
    """ No items, only parameters """
    return ((),
            {'_valid_items': [],
             '_valid_params': ['id', 'and']})


class TestAutoNode(TestCase):
    """ Unit test for AutoNode
    """

    def test_auto_node_contents(self):
        """ Auto node should create a template """
        self.assertEqual(str(TestNode), 'testNode { field1 field2 }')

    def test_extend_auto_node(self):
        """ Auto node should create an extended node from template """
        self.assertEqual(str(TestNode('extra')), 'testNode { field1 field2 extra }')

    def test_auto_node_is_constant(self):
        """ Changing auto node will raise an exception """
        var = TestNode
        # Calling var.add('extra') will raise an exception
        self.assertRaises(TypeError, var.add, 'extra')

    def test_extended_auto_node_is_not_constant(self):
        """ Auto node should create an extended node from template """
        var = TestNode()
        self.assertEqual(str(var.add('other')),
                         'testNode { field1 field2 other }')

    def test_extending_valid_item(self):
        """ Auto node should create an extended node from template """
        var = TestFixedNode('field3')
        self.assertEqual(str(var),
                         'testFixedNode { field1 field2 field3 }')

    def test_extending_valid_node_item(self):
        """ Auto node should create an extended node from template """
        field3 = graphql.GraphQLNode('field3', 'subitem1', 'subitem2')
        var = TestFixedNode(field3)
        self.assertEqual(str(var),
                         'testFixedNode { field1 field2 '
                         'field3 { subitem1 subitem2 } }')

    def test_extending_invalid_item(self):
        """ Only allow to add items in the _valid_items list """
        var = TestFixedNode()
        self.assertRaises(ValueError, var.add, 'extra')
        self.assertEqual(str(var),
                         'testFixedNode { field1 field2 }')

    def test_extending_invalid_node_item(self):
        """ Only allow to add items in the _valid_items list """
        var = TestFixedNode()
        extra = graphql.GraphQLNode('extra', 'subitem1', 'subitem2')
        self.assertRaises(ValueError, var.add, extra)
        self.assertEqual(str(var),
                         'testFixedNode { field1 field2 }')

    def test_extending_invalid_item_empy_list(self):
        """ Only allow to add items in the _valid_items list
            Empty list means no items can be added """
        var = TestNoItemsNode()
        self.assertRaises(ValueError, var.add, 'extra')
        self.assertEqual(str(var), 'testNoItemsNode')

    def test_extending_valid_params(self):
        """ Only allow to add params in the _valid_params list """
        var = TestNoItemsNode(_and=True, id=12)
        self.assertEqual(str(var), 'testNoItemsNode(and: true, id: "gid://12")')

    def test_extending_invalid_params(self):
        """ Only allow to add params in the _valid_params list """
        var = TestFixedNode(_and=True)
        var.add('field3', id=12)
        self.assertEqual(str(var), 'testFixedNode(and: true, id: "gid://12")'
                                   ' { field1 field2 field3 }')
        self.assertRaises(ValueError, var.add, field2='extra')

    def test_input_constructor(self):
        """ Input works differently to other auto-nodes """
        var = graphql.Input('id', 'or', 'name', name='me')
        self.assertEqual(str(var), 'input(name: "me")')
        var.add(id=21)
        self.assertEqual(str(var), 'input(name: "me", id: "gid://21")')

class TestFindMethods(TestCase):
    """ Unit test for find_in_dict
    """

    def test_find_all_values(self):
        """ Assert all found nodes have the right value """
        data, reference = load_yaml_data(f'{TEST_DIR}/data/test_find_all_values.yml')
        found = graphql.find_all_values(data, 'pipeline_nodes')
        self.maxDiff = None
        self.assertListEqual(found, reference)

    def test_find_all_values(self):
        """ Assert all found nodes have the right value """
        data, reference = load_yaml_data(f'{TEST_DIR}/data/test_find_all_containers.yml')
        found = graphql.find_all_containers(data, 'iid')
        self.maxDiff = None
        self.assertListEqual(found, reference)
