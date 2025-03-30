"""
GraphQL basic node
"""


class GraphQLField:
    """
    GraphQL node or mutation
    """
    def __init__(self, _name, *args,
                 _alias='', _gid_path='', **kwargs):
        """
        Create a node with ONE parameter
        Multi-parameters are not supported because I don't understand how they work
        """
        self.params = ""
        self.alias = ""
        self.name = _name
        self.alias = _alias
        self.nude = kwargs.pop('_nude') if '_nude' in kwargs else False
        if self.nude:
            if len(args) != 1:
                raise ValueError('Only one nude item can be added')
            if not isinstance(args[0], GraphQLField):
                raise ValueError('Nude items must be of type GraphQLField')
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
        Add items to the field
        """
        if self.nude:
            self.items[0].add(*args)
        else:
            self.items.extend(list(args))

    def add_to_all(self, *args):
        """
        Add items to the pipeline query fields
        """
        for item in self.items:
            if isinstance(item, GraphQLField):
                item.add(*args)

    def to_string(self, indentation=0, separator=' ', nude=False):
        """
        Convert node to a string representation
        """
        if nude:
            next_indention = indentation
            indentation = indentation - 2
        else:
            next_indention = indentation + 2
        spaces = ' ' * indentation
        prev_spaces = ' ' * (indentation - 2)
        # Start with the name
        lines = []
        field = f'{self.alias}: {self.name}' if self.alias else self.name
        if self.params:
            field = f'{field}{self.params}'
        if self.items:
            field = field + ' ' if self.name else field
            field = field + '{' if not nude else ''
            if field:
                lines.append(prev_spaces + field)
            for item in self.items:
                if not isinstance(item, GraphQLField):
                    lines.append(spaces + str(item))
                else:
                    line = item.to_string(next_indention, separator, self.nude)
                    lines.append(line)
            if not nude:
                lines.append(prev_spaces + '}')
        else:
            lines = [field]
        return separator.join(lines)

    def __repr__(self):
        return self.to_string(2, '\n')

    def __str__(self):
        return self.to_string()


class NodesQL(GraphQLField):
    """
    A simple 'nodes' wrapper
    """
    def __init__(self, _name, *args,
                 _node_alias=None, **kwargs):
        """
        Use alias instead of name
        """
        _alias = kwargs.pop('_alias') if '_alias' in kwargs else ''
        _nude = kwargs.pop('_nude') if '_nude' in kwargs else False
        node_alias = _node_alias if _node_alias is not None else f'{_name}_nodes'
        if _nude:
            if len(args) != 1:
                raise ValueError('Only one nude item can be added')
            if not isinstance(args[0], GraphQLField):
                raise ValueError('Nude items must be of type GraphQLField')
            self.node = args[0]
        else:
            self.node = GraphQLField('', *args)
        self.alias_node = GraphQLField('nodes', self.node, _alias=node_alias, _nude=True)
        super().__init__(_name, self.alias_node, _alias=_alias, **kwargs)

    def add(self, *args):
        """
        Add items to the node
        """
        self.node.items.extend(list(args))
