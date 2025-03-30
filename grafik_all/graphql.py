"""
GraphQL basic node
"""
# pylint: disable=protected-access


from typing import Any, Optional


class GraphQLNode:
    """
    GraphQL node or mutation
    """
    def __init__(self, _name, *args, _alias='', **kwargs):
        """
        Create a node with ONE parameter
        Multi-parameters are not supported because I don't understand how they work
        """
        self.name = _name
        self.alias = _alias if _alias else ''
        self.params = {}
        self.items = []
        self._nude = kwargs.pop('_nude') if '_nude' in kwargs else False
        self._gid_path = kwargs.pop('_gid_path') if '_gid_path' in kwargs else ''
        self._add_params(**kwargs)  # self.params is a shallow copy of kwargs
        if self._nude:
            if len(args) != 1:
                raise ValueError('Nude nodes require exactly one parameter')
            if not isinstance(args[0], GraphQLNode):
                raise TypeError('Nude items must be of type GraphQLNode')
        self.add(*args)

    def add(self, *args, **kwargs):
        """
        Add items or parameters to the node
        """
        if args:
            self._add_items(*args)
        if kwargs:
            self._add_params(**kwargs)

    def add_to_all(self, *args, **kwargs):
        """
        Add items to the pipeline query fields
        """
        for item in [i for i in self.items if isinstance(i, GraphQLNode)]:
            item.add(*args, **kwargs)

    def first(self, first: int):
        """
        Pagination helper
        """
        self.add(first=first)

    def after(self, after: Any):
        """
        Pagination helper
        """
        self.add(after=after)

    def _drop(self, item):
        if item in self.items:
            self.items.remove(item)
        elif isinstance(item, str):
            i = GraphQLNode(item)
            self._drop(i)

    def _add_items(self, *args):
        """
        Add items to the field
        """
        if len(self.items) <= 0 and self._nude:
            # Add initial nude node
            self.items.extend(args)
            return
        if self._nude:
            self.items[0].add(*args)
            return
        for item in args:
            self._drop(item)
            self.items.append(item)

    def _add_params(self, **kwargs):
        """
        Add items to the field
        """
        for i, v in kwargs.items():
            i = i.lstrip('_')
            v = self._get_gid(self._gid_path, v) if i == 'id' else v
            self.params[i] = v


    def _get_gid(self, _gid_path, _id):
        if not str(_id).startswith('gid://'):
            prefixes = _gid_path.split('/')
            prefix = ''
            for segment in prefixes:
                if not segment:
                    continue
                if _id.startswith(segment):
                    break
                prefix = f'{prefix}/{segment}' if prefix else segment
            _id = _id if not prefix else f'{prefix}/{_id}'
            _id = f'gid://{_id}'
        return _id

    def _params_to_string(self):
        params = []
        for i, v in self.params.items():
            if isinstance(v, str):
                params.append(f'{i}: "{v}"')
            elif isinstance(v, GraphQLNode):
                params.append(f'{i}: {{{v._params_to_string()}}}')
            else:
                params.append(f'{i}: {str(v)}')
        return ", ".join(params)

    def _items_to_string(self, indentation, separator):
        spaces = ' ' * indentation
        next_indention = indentation + 2 if indentation > 0 else 0
        for item in self.items:
            if not isinstance(item, GraphQLNode):
                yield spaces + str(item)
            else:
                yield item._to_string(next_indention, separator, self._nude)

    def _to_string(self, indentation=0, separator=' ', nude=False):
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
            # Add params if they exist
            field = f'{field}({self._params_to_string()})'
        if self.items:
            # Finally all the fields
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
        return self._to_string(2, '\n')

    def __str__(self):
        return self._to_string()

    def __eq__(self, other):
        if not isinstance(other, GraphQLNode):
            return False
        return self.name == other.name and self.alias == other.alias


class AnonymousNode(GraphQLNode):
    """
    Node without name
    """
    def __init__(self, *args, **kwargs):
        """
        Create a node without name
        """
        self._no_alias = kwargs.pop('_alias') if '_alias' in kwargs else ''
        super().__init__('', *args, **kwargs)
        self.name = self.alias = ''


class NodesQL(GraphQLNode):
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
            if not isinstance(args[0], GraphQLNode):
                raise ValueError('Nude items must be of type GraphQLNode')
            self.node = args[0]
        else:
            self.node = GraphQLNode('', *args)
        self.alias_node = GraphQLNode('nodes', self.node, _alias=node_alias, _nude=True)
        super().__init__(_name, self.alias_node, _alias=_alias, **kwargs)

    def add_to_nodes(self, *args):
        """
        Add items to the node
        """
        self.node.items.extend(list(args))


class GraphQLEnum:
    """
    Basic class decorator to create GraphQL enums
    The final result should be just a string, except it is not of type str
    """
    def __init__(self, getitems):
        self._getitems = getitems
        self._name = getitems.__name__
        self.__doc__ = getitems.__doc__
        self._items = getitems(self)

    def __getattr__(self, item):
        if item in {'__name__', '__qualname__'}:
            return self._name
        if item == 'lower':
            return self._name.lower()
        if item in self._items:
            return self._items[item]

        raise AttributeError(f'No such item: {item}')

    def __repr__(self):
        return self._name.upper()

    def __eq__(self, other):
        return self._name == str(other)


class AutoNode(GraphQLNode):
    """
    Class decorator to create a simple node from function template
    """
    def __init__(self, node_items):
        self._node_items = node_items
        self._name = node_items.__name__[0].lower() + node_items.__name__[1:]
        self.__doc__ = node_items.__doc__
        _items, _params = node_items()
        super().__init__(self._name, *_items, **_params)


@AutoNode
def PageInfo():  # pylint: disable=invalid-name
    """
    Create a graphql node with pagination info
    """
    return ('endCursor', 'startCursor', 'hasNextPage'), {}


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
