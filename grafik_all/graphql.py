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
    flat = []
    for x in non_flat:
        if isinstance(x, list):
            flat.extend(x)
        elif x is not None:
            flat.append(x)
    return flat

def find_all_containers(dictionary: dict, item: str, value: Optional[Any] = None):
    """
    Find all entries in dictionary matching 'item' and return a list of values
    """
    return [x for _, x in find_in_dict(dictionary, item, value)]


def _param_to_graphql_rep(item: any):
    """
    Convert any item in parameters to its graphql representation.
    Strings require double quotations, but other types don't.
    """
    if isinstance(item, str):
        return f'"{item}"'
    elif isinstance(item, bool):
        return f'{str(item).lower()}'
    elif isinstance(item, GraphQLNode):
        return f'{{ {item._params_to_string()} }}'
    elif isinstance(item, list):
        res = []
        for v in item:
            res.append(_param_to_graphql_rep(v))
        return '[ ' + ', '.join(res) + ' ]'
    else:
        return str(item)

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
        self._valid_params = None
        self._valid_items = None
        self._gid_path = ''
        self._add_params(**kwargs)  # self.params is a shallow copy of kwargs
        self.add(*args)

    def add(self, *args, **kwargs):
        """
        Add items or parameters to the node
        """
        if self._constant:
            raise TypeError("Cannot update a const!")
        if kwargs:
            self._add_params(**kwargs)
        if args:
            self._add_items(*args)
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

    def matching_gid(self, other: str):
        """
        Return 'id' if 'other' gid is the same type as this node
        Return empty string otherwise
        """
        other = str(other)
        other_id = [x for x in other.split('/') if x]
        my_id = [x for x in self._gid_path.split('/') if x]
        needs_full_id = False
        if 'gid:' in other_id:
            other_id.remove('gid:')
            needs_full_id = True
        if not other_id:
            return ''
        id_num = other_id.pop()
        for i in reversed(my_id):
            if not other_id and needs_full_id:
                return ''
            if other_id and other_id.pop() != i:
                return ''
        return id_num if id_num.isdigit() else ''

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
            if self._valid_items is not None and item not in self._valid_items:
                error_msg = f"Item '{item}' is not valid"
                raise ValueError(error_msg)
            self._drop(item)
            self.items.append(item)

    def _add_params(self, **kwargs):
        """
        Add items to the field
        """
        # Process special parameters first
        _nude_node: GraphQLNode = kwargs.pop('_node') if '_node' in kwargs else None
        _valid_params = kwargs.pop('_valid_params') if '_valid_params' in kwargs else None
        _valid_items = kwargs.pop('_valid_items') if '_valid_items' in kwargs else None
        _gid_path = kwargs.pop('_gid_path') if '_gid_path' in kwargs else ''
        if _nude_node:
            if not isinstance(_nude_node, GraphQLNode):
                raise ValueError('Nude items must be of type GraphQLNode')
            self._nude = _nude_node is not None
            self.items = [_nude_node]
        self._valid_params = _valid_params if _valid_params is not None else self._valid_params
        self._valid_items = _valid_items if _valid_items is not None else self._valid_items
        self._gid_path = _gid_path if _gid_path is not None else self._gid_path
        # Process other parameters
        for i, v in kwargs.items():
            i = i.lstrip('_')
            v = self._get_gid(self._gid_path, v) if i == 'id' else v
            if self._valid_params is not None and i not in self._valid_params:
                error_msg = f"Parameter '{i}' is not valid"
                raise ValueError(error_msg)
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
            params.append(f'{i}: {_param_to_graphql_rep(v)}')
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
        if isinstance(other, str):
            return self.name == other or f'{self.alias}: {self.name}' == other
        if isinstance(other, GraphQLNode):
            return self.name == other.name and self.alias == other.alias
        return False

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
        _top = kwargs.pop('_top') if '_top' in kwargs else []
        node_alias = _node_alias if _node_alias is not None else f'{_name}_nodes'
        if _node:
            if not isinstance(_node, GraphQLNode):
                raise ValueError('Nude items must be of type GraphQLNode')
            self.node = _node
            nude_node_name = self.node.alias if self.node.alias else self.node.name
            if _node_alias:
                nude_node_name = _node_alias
            elif nude_node_name:
                node_alias = nude_node_name
            else:
                node_alias = None
            if len(args) != 0:
                pass  # What to do if there are args? Ignore them looks safe
        else:
            node_alias = node_alias if node_alias or _node_alias else None
            self.node = GraphQLNode(node_alias, *args)
        self.alias_node = GraphQLNode('nodes', _node=self.node, _alias=node_alias)
        super().__init__(_name, *_top, self.alias_node, _alias=_alias, **kwargs)

    def add_to_nodes(self, *args):
        """
        Add items to the 'nodes' item
        """
        self.node.items.extend(list(args))


class GraphQLInput(GraphQLNode):
    """
    Input class. Inputs have names, but do not have any items, and their string
    representation looks almost like a dictionary.
    Inputs are used as parameters for other nodes. They are different from
    simple dictionaries in that their string representation is aware of graphql
    uniqueness like booleans being lowercase, and gid's needing 'gid://'; plus
    some additional spaces to make it both visually consistent with the rest of
    the library and obviously different from a dictionary.
    """
    def __init__(self, _name, *args, **kwargs):
        """ Input class """
        _valid_parmas = list(args) if args else None
        super().__init__(_name, _valid_params=_valid_parmas, _valid_items=[], **kwargs)


class GraphQLEnum:
    """
    Basic class decorator to create GraphQL enums
    The final result is a case-insensitive string.
    It can be compared, but not assigned, to strings.
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
        if item == 'upper':
            return self._name.upper()
        if item in self._items:
            return self._items[item]

        raise AttributeError(f'No such item: {item}')

    def __repr__(self):
        """ Just a string """
        return self._name

    def __eq__(self, other):
        """ Enum tests are case-insensitive """
        return self._name.lower() == str(other).lower()

    def __hash__(self):
        """ Hash the lowercase string """
        return hash(self._name.lower())


def AutoNode(base_class):
    """
    Decorator to create a class derived from GraphQLNode, filled with the
    data returned by a function.
    See functions with @AutoNode down this file to understand what it means.
    """
    class DerivedNode(base_class):
        """
        Class decorator to create a simple node from function template
        """
        def __init__(self, node_items) -> None:
            assert issubclass(base_class, GraphQLNode)
            self._node_func = node_items
            self.__doc__ = node_items.__doc__
            self._items, self._params = node_items()
            self._name = self._params.pop('_name') if '_name' in self._params \
                        else node_items.__name__[0].lower() + node_items.__name__[1:]
            super().__init__(self._name, *self._items, **self._params)
            self._constant = True

        def __call__(self, *args, **kwargs) -> GraphQLNode:
            """ Calling the decorated method will work as a constructor """
            for i, v in self._params.items():
                if i not in kwargs:
                    kwargs[i] = v
            if '_node' in kwargs:  # Use node attributes if a node is provided
                return base_class(self.name, *args, **kwargs)
            return base_class(self.name, *self._items, *args, **kwargs)

    return DerivedNode


#######################################################
# Typical nodes expected in all graphql implementations
#######################################################

@AutoNode(GraphQLNode)
def Query(*_, **__) -> GraphQLNode:  # pylint: disable=invalid-name
    """
    Create a query root node
    """
    return (), {}


@AutoNode(GraphQLNode)
def Mutation(*_, **__) -> GraphQLNode:  # pylint: disable=invalid-name
    """
    Create a mutation root node
    """
    return (), {}


@AutoNode(GraphQLNode)
def PageInfo(*_, **__) -> GraphQLNode:  # pylint: disable=invalid-name
    """
    Create a graphql node with pagination info
    """
    return ('endCursor', 'startCursor', 'hasNextPage'), {}


@AutoNode(GraphQLInput)
def Input(*_, **__) -> GraphQLInput:  # pylint: disable=invalid-name
    """
    Create a generic input node without any items
    Arguments are treated as a list of valid parameters
    """
    return ((), {})
