"""
GraphQL basic node
"""


class GraphQLNode:
    """
    GraphQL node or mutation
    """
    def __init__(self, _name, *args, _gid_path="", **kwargs):
        """
        Create a node with ONE parameter
        Multi-parameters are not supported because I don't understand how they work
        """
        print(_name)
        self.params = ""
        self.alias = ""
        self.name = _name
        self.items = list(args)
        for key, value in kwargs.items():
            if key == "id" and not value.startswith('gid://'):
                prefixes = _gid_path.split("/")
                prefix = ''
                for segment in prefixes:
                    if not segment:
                        continue
                    if value.startswith(segment):
                        break
                    prefix = f'{prefix}/{segment}' if prefix else segment
                value = value if not prefix else f'{prefix}/{value}'
                self.params = f'(id: "gid://{value}")'
            else:
                self.params = f'({key}: "{value}")'

    def add(self, *args):
        """
        Add items to the node
        """
        self.items.extend(list(args))

    def to_string(self, indentation=0, separator=' '):
        """
        Convert node to a string representation
        """
        spaces = ' ' * indentation
        next_indention = indentation + 2 if indentation else 0
        # Start with the name
        node = f'{self.alias}: {self.name}' if self.alias else self.name
        if self.params:
            node = f'{node}{self.params}'
        if self.items:
            node = node + ' {' + separator
            for item in self.items:
                line = str(item) if not isinstance(item, GraphQLNode) \
                    else item.to_string(next_indention, separator)
                node = node + spaces + line + separator
            node = node + ' ' * (indentation - 2) + '}'
        return node

    def __repr__(self):
        return self.to_string(2, '\n')

    def __str__(self):
        return self.to_string()


class NodeQL(GraphQLNode):
    """
    A simple 'nodes' wrapper
    """
    def __init__(self, _name, *args, _gid_path="", **kwargs):
        """
        Use alias instead of name
        """
        super(NodeQL, self).__init__('nodes', *args, _gid_path, **kwargs)
        self.alias = _name
