"""
GraphQL basic node
"""


class GraphQLNode:
    """
    GraphQL node or mutation
    """
    def __init__(self, name, *args, **kwargs):
        """
        Create a node with ONE parameter
        Multi-parameters are not supported because I don't understand how they work
        """
        self.params = ""
        self.alias = ""
        self.name = name
        self.items = list(args)
        for key, value in kwargs.items():
            self.params = f'(id: "gid://{value}")' if key == "id" else \
                          f'({key}: "{value}")'

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
