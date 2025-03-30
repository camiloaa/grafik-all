#!/bin/env python3
"""
Test subparser module
"""
# pylint: disable=invalid-name


from unittest import TestCase
from git_extra.lib import graphql


@graphql.GraphQLEnum
def CONSTANT(self):
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
        nodes_query = graphql.NodesQL('project', nodes_items, id=12, _nude=True)
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
