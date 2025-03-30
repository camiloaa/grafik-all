"""
GraphQL basic node
"""


from typing import Any, Optional


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
        self.params = kwargs
        if self.nude:
            if len(args) != 1:
                raise ValueError('Only one nude item can be added')
            if not isinstance(args[0], GraphQLField):
                raise ValueError('Nude items must be of type GraphQLField')
        self.items = list(args)
        if 'id' in self.params and not self.params['id'].startswith('gid://'):
            value = self.params['id']
            prefixes = _gid_path.split("/")
            prefix = ''
            for segment in prefixes:
                if not segment:
                    continue
                if value.startswith(segment):
                    break
                prefix = f'{prefix}/{segment}' if prefix else segment
            value = value if not prefix else f'{prefix}/{value}'
            self.params['id'] = f'gid://{value}'

    def add(self, *args):
        """
        Add items to the field
        """
        if self.nude:
            self.items[0].add(*args)
        else:
            self.items.extend(list(args))

    def add_params(self, **kwargs):
        """
        Add items to the field
        """
        for i, v in kwargs.items():
            self.params[i] = v

    def add_to_all(self, *args):
        """
        Add items to the pipeline query fields
        """
        for item in self.items:
            if isinstance(item, GraphQLField):
                item.add(*args)

    def _params_to_string(self):
        params = []
        for i, v in self.params.items():
            if isinstance(v, str):
                params.append(f'{i}: "{v}"')
            else:
                params.append(f'{i}: {str(v)}')
        return f'({" ".join(params)})'

    def _items_to_string(self, indentation, separator):
        spaces = ' ' * indentation
        next_indention = indentation + 2
        for item in self.items:
            if not isinstance(item, GraphQLField):
                yield spaces + str(item)
            else:
                yield item.to_string(next_indention, separator, self.nude)

    def to_string(self, indentation=0, separator=' ', nude=False):
        """
        Convert node to a string representation
        """
        if nude:
            indentation = indentation - 2
        spaces = ' ' * (indentation - 2)
        # Start with the name
        lines = []
        field = f'{self.alias}: {self.name}' if self.alias else self.name
        if self.params:
            field = f'{field}{self._params_to_string()}'
        if self.items:
            field = field + ' ' if self.name else field
            field = field + '{' if not nude else ''
            if field:
                lines.append(spaces + field)
            lines.extend(list(self._items_to_string(indentation, separator)))
            if not nude:
                lines.append(spaces + '}')
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


def find_in_dict(dictionary: dict, item: str, value: Optional[Any] = None):
    """
    Find item in dictionary
    """
    if isinstance(dictionary, dict):
        if item in dictionary:
            if value is None or dictionary[item] == value:
                yield (dictionary[item], dictionary)
        for _, i in dictionary.items():
            if isinstance(i, (list, dict)):
                yield from find_in_dict(i, item, value)
    if isinstance(dictionary, list):
        for i in dictionary:
            if isinstance(i, (list, dict)):
                yield from find_in_dict(i, item, value)
    return


def find_all_values(dictionary: dict, item: str, value: Optional[Any] = None):
    """
    Find all entries in dictionary matching 'item' and return a list of values
    """
    non_flat = [x for x, _ in find_in_dict(dictionary, item, value)]
    return [item for sublist in non_flat for item in sublist]


def find_all_containers(dictionary: dict, item: str, value: Optional[Any] = None):
    """
    Find all entries in dictionary matching 'item' and return a list of values
    """
    return [x for _, x in find_in_dict(dictionary, item, value)]


class _StatusEnum:
    """
    Basic class decorator to create gitlab pipeline statuses
    The final result should be just a string, except it is not of type str
    """
    def __init__(self, getitem):
        self._getitem = getitem
        self._name = getitem.__name__
        self.__doc__ = getitem.__doc__

    def __getattr__(self, item):
        if item in {'__name__', '__qualname__'}:
            return self._name
        if item == 'lower':
            return self._name.lower()
        if item == 'color':
            return self._getitem(self)

        raise AttributeError(item)

    def __repr__(self):
        return self._name.upper()

    def __eq__(self, other):
        return self._name == str(other)
