"""
GraphQL basic node
"""
# pylint: disable=protected-access


from typing import Any, Optional


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


class GraphQLNode:
    """
    GraphQL node or mutation
    """
    def __init__(self, _name, *args, _alias='', **kwargs):
        """
        Create a node with arbitrary items and parameters.
        Special parameters start with underscore:
            - _node: Use _node as a nude item, meaning that the created GraphQLNode
              will not have any ites, but will treat items in _node as their own.
              Useful when several nodes share the same items.
            - _gid_path: Path to use when 'id=value' is used.
        """
        self.name = _name
        self.alias = _alias if _alias else ''
        self.params = {}
        self.items = []
        self._nude = False
        self._constant = False
        self._add_params(**kwargs)  # self.params is a shallow copy of kwargs
        self.add(*args)

    def add(self, *args, **kwargs):
        """
        Add items or parameters to the node
        """
        if self._constant:
            raise TypeError("Cannot update a const!")
        if args:
            self._add_items(*args)
        if kwargs:
            self._add_params(**kwargs)
        return self

    def add_to_all(self, *args, **kwargs):
        """
        Add items to all GraphQLNodes
        """
        if self._constant:
            raise TypeError("Cannot update a const!")
        for item in self.items:
            if isinstance(item, GraphQLNode):
                item.add(*args, **kwargs)
        return self

    def first(self, first: int):
        """
        Pagination helper
        """
        if self._constant:
            raise TypeError("Cannot update a const!")
        self.add(first=first)

    def after(self, after: Any):
        """
        Pagination helper
        """
        if self._constant:
            raise TypeError("Cannot update a const!")
        return self.add(after=after)

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
        _nude_node: GraphQLNode = kwargs.pop('_node') if '_node' in kwargs else None
        self._gid_path = kwargs.pop('_gid_path') if '_gid_path' in kwargs else ''
        if _nude_node:
            if not isinstance(_nude_node, GraphQLNode):
                raise ValueError('Nude items must be of type GraphQLNode')
            self._nude = _nude_node is not None
            self.items = [_nude_node]
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
                if str(_id).startswith(segment):
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
            elif isinstance(v, bool):
                params.append(f'{i}: {str(v).lower()}')
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
        lines = []
        spaces = ' ' * (indentation - 2)
        # Start with the name
        if nude:
            indentation = indentation - 2
            field = ''
        else:
            field = f'{self.alias}: {self.name}' if self.alias else self.name
        if self.params and not nude:
            # Add params if they exist
            field = f'{field}({self._params_to_string()})'
        if self.items:
            # Add curly bracets around items if necessary
            field = field + ' ' if field else field
            field = field + '{' if not nude else field
            if field:
                lines.append(spaces + field)
            # Finally, add all the fields
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

    def __call__(self, *args, **kwargs):
        """"""
        self.add(*args, **kwargs)
        return self


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
        _node = kwargs.pop('_node') if '_node' in kwargs else False
        node_alias = _node_alias if _node_alias is not None else f'{_name}_nodes'
        if _node:
            if not isinstance(_node, GraphQLNode):
                raise ValueError('Nude items must be of type GraphQLNode')
            self.node = _node
            node_alias = self.node.name if self.node.name and not _node_alias else node_alias
            if len(args) != 0:
                pass  # What to do if there are args? Ignore them looks safe
        else:
            self.node = GraphQLNode(node_alias, *args)
        self.alias_node = GraphQLNode('nodes', _node=self.node, _alias=node_alias)
        super().__init__(_name, self.alias_node, _alias=_alias, **kwargs)

    def add_to_nodes(self, *args):
        """
        Add items to the 'nodes' item
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


def AutoNode(base_class):
    """
    Decorator to create a class derived from GraphQLNode, filled with the
    data returned by a function.
    See PageInfo function down this file to understand what it means.
    """
    class DerivedNode(base_class):
        """
        Class decorator to create a simple node from function template
        """
        def __init__(self, node_items):
            assert issubclass(base_class, GraphQLNode)
            self._nude_node_items = node_items
            self._name = node_items.__name__[0].lower() + node_items.__name__[1:]
            self.__doc__ = node_items.__doc__
            self._items, self._params = node_items()
            super().__init__(self._name, *self._items, **self._params)
            self._constant = True

        def __call__(self, *args, **kwargs):
            """ """
            for i, v in self._params.items():
                if i not in kwargs:
                    kwargs[i] = v
            return base_class(self.name, *self._items, *args, **kwargs)

    return DerivedNode


@AutoNode(GraphQLNode)
def PageInfo(*_, **__):  # pylint: disable=invalid-name
    """
    Create a graphql node with pagination info
    """
    return ('endCursor', 'startCursor', 'hasNextPage'), {}
