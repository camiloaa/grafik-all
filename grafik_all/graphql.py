"""
GraphQL basic node
"""


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
        self.add_params(**kwargs)  # self.params is a shallow copy of kwargs
        if self._nude:
            if len(args) != 1:
                raise ValueError('Nude nodes require exactly one parameter')
            if not isinstance(args[0], GraphQLNode):
                raise TypeError('Nude items must be of type GraphQLNode')
        self.add(*args)

    def add(self, *args, **kwargs):
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

    def add_params(self, **kwargs):
        """
        Add items to the field
        """
        for i, v in kwargs.items():
            v = self._get_gid(self._gid_path, v) if i == 'id' else v
            self.params[i] = v

    def add_to_all(self, *args):
        """
        Add items to the pipeline query fields
        """
        for item in self.items:
            if isinstance(item, GraphQLNode):
                item.add(*args)

    def add_params_to_all(self, **kwargs):
        """
        Add items to the pipeline query fields
        """
        for item in self.items:
            if isinstance(item, GraphQLNode):
                item.add_params(**kwargs)

    def first(self, first: int):
        """
        Pagination helper
        """
        self.add(first=first)

    def after(self, after: int):
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
            else:
                params.append(f'{i}: {str(v)}')
        return f'({", ".join(params)})'

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
        return self._to_string(2, '\n')

    def __str__(self):
        return self._to_string()

    def __eq__(self, other):
        if not isinstance(other, GraphQLNode):
            return False
        return self.name == other.name and self.alias == other.alias


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
