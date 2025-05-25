"""
GraphQL basic node
"""
# pylint: disable=protected-access


from types import FunctionType
from typing import Any, Optional, Union


def find_in_dict(dictionary: dict, items: Union[str, list],
                 values: Optional[Any] = None,
                 depth: Optional[int] = -1):
    """
    Find items in dictionary by name
    """
    values = [] if not values else values
    if not isinstance(items, list):
        items = [items]
    if not isinstance(values, list):
        values = [values]
    if isinstance(dictionary, dict):
        for i in items:
            if i in dictionary and (not values or dictionary[i] in values):
                yield (dictionary[i], dictionary)
        if depth == 0:
            return
        for _, i in dictionary.items():
            if isinstance(i, (list, dict)):
                yield from find_in_dict(i, items, values=values, depth=depth - 1)
    if isinstance(dictionary, list):
        for i in dictionary:
            if isinstance(i, (list, dict)) and depth != 0:
                yield from find_in_dict(i, items, values=values, depth=depth - 1)


def find_all_items(dictionary: dict, items: str,
                   values: Optional[Any] = None,
                   depth: Optional[int] = -1):
    """
    Find all entries in dictionary matching 'items' and return a list of values
    """
    non_flat = [x for x, _ in find_in_dict(dictionary, items, values, depth)]
    flat = []
    for x in non_flat:
        if isinstance(x, list):
            flat.extend(x)
        elif x is not None:
            flat.append(x)
    return flat


def find_all_containers(dictionary: dict, items: str,
                        values: Optional[Any] = None,
                        depth: Optional[int] = -1):
    """
    Find all entries in dictionary matching 'items' and return a list of values
    """
    return [x for _, x in find_in_dict(dictionary, items, values, depth)]


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
        Special parameters start with underscore. If a parameter starts with
        underscore but it is not a special parameter, underscores are dropped.
        This is useful when graphql parameters have the same name of python
        keywords; for example graphql parameter 'if' can be passed as '_if'.

        Parameters:
        :param _alias: Node alias.
        :param _node: Use _node as a nude item, meaning that the created GraphQLNode
            will not have any items, but will treat items in _node as their own.
            Useful when several nodes share the same items.
        :param _gid_path: Path to use when 'id=value' is used.
        :param _valid_params: Parameters to be recognized by the graphql node.
        :param _valid_items: Items to be recognized by the graphql node.

        Subclasses might have their own special parameters.
        """
        _name = '' if not _name else _name
        if not isinstance(_name, str):
            raise TypeError("_name must be a string")
        split_name = [i.strip() for i in _name.split(':')]
        self._name = split_name.pop()
        if self._name and not self._name.isidentifier():
            raise TypeError(f"_name {self._name} must be alphanumeric")
        other_alias = ''.join(split_name)
        self._alias = _alias if _alias else other_alias
        self._params = {}
        self._items = []
        self._nude = False
        self._constant = False
        self._valid_params = None
        self._valid_items = None
        self._gid_path = ''
        self.add(*args, **kwargs)

    def items(self):
        """Return items"""
        if self._nude:
            return self._items[0].items()
        return self._items

    def params(self):
        """Return items"""
        if self._nude:
            return self._items[0].params()
        return self._params

    def name(self):
        """Node name as will be shown in the response"""
        return self._name if not self._alias else self._alias

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
        for item in self._items:
            if isinstance(item, GraphQLNode):
                item.add(*args, **kwargs)
        return self

    def update(self, other):
        """Add the contents of another node to this one"""
        if self._constant:
            raise TypeError("Cannot update a const!")
        if not isinstance(other, GraphQLNode):
            raise TypeError(f"Update requires a GraphQLNode. Got {type(other)}")
        if self._nude:
            self._items[0].update(other)
        else:
            for i in other.items():
                existing = self.__getitem__(i, default=None)
                if existing and isinstance(existing, GraphQLNode):
                    if isinstance(i, GraphQLNode):
                        existing.update(i)
                    continue  # Do not update if the other item is not a node
                self.add(i)
        self.add(**other.params())

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

    def pretty(self, indentation=2):
        """Print a pretty version of this node"""
        return self._to_string(indentation, indentation, '\n')

    def _drop(self, item):
        if item in self._items:
            self._items.remove(item)
        elif isinstance(item, str):
            i = GraphQLNode(item)
            self._drop(i)

    def _add_items(self, *args):
        """
        Add items to the field
        """
        if self._nude:
            self._items[0].add(*args)
            return
        for item in args:
            if self._valid_items is not None and item not in self._valid_items:
                error_msg = f"Item '{item}' is not valid"
                raise ValueError(error_msg)
            if isinstance(item, (GraphQLNode, str)):
                self._drop(item)
                self._items.append(item)
            elif isinstance(item, dict):
                for i, v in item.items():
                    t_item = GraphQLNode(i, *v)
                    self._drop(t_item)
                    self._items.append(t_item)
            else:
                raise TypeError(f"Invalid type for item {item} ({type(item)})")

    def _add_params(self, **kwargs):
        """
        Add items to the field, initial underscores are dropped.
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
            self._items = [_nude_node]
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
            self._params[i] = v

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
        for i, v in self._params.items():
            params.append(f'{i}: {_param_to_graphql_rep(v)}')
        return ", ".join(params)

    def _items_to_string(self, indentation, size, separator):
        spaces = ' ' * indentation
        next_indentation = indentation + 2 if indentation > 0 else 0
        for item in self._items:
            if not isinstance(item, GraphQLNode):
                yield spaces + str(item)
            else:
                yield item._to_string(next_indentation, size, separator, self._nude)

    def _to_string(self, indentation=0, size=2, separator=' ', nude=False):
        """
        Convert node to a string representation
        """
        lines = []
        spaces = ' ' * (indentation - size)
        # Start with the name
        if nude:
            indentation = indentation - size
            field = ''
        else:
            field = f'{self._alias}: {self._name}' if self._alias else self._name
        if self._params and not nude:
            # Add params if they exist
            field = f'{field}({self._params_to_string()})'
        if self._items:
            # Add curly brackets around items if necessary
            field = field + ' ' if field else field
            field = field + '{' if not nude else field
            if field:
                lines.append(spaces + field)
            # Finally, add all the fields
            lines.extend(list(self._items_to_string(indentation, size, separator)))
            if not nude:
                lines.append(spaces + '}')
        else:
            lines = [spaces + field]
        return separator.join(lines)

    def __repr__(self):
        return self._to_string()

    def __eq__(self, other):
        """Return true if two nodes would return the same id in a query
           That would be the case if they have the same alias,
           or if one'a alias is the same name as the other's name
        """
        other_alias = ''
        other_name = ''
        if isinstance(other, str):
            n = other.split(':')
            other_name = n.pop().strip()
            other_alias = n.pop().strip() if n else ''
        if isinstance(other, GraphQLNode):
            other_name = other._name
            other_alias = other._alias if other._alias else ''
        if self._alias and other_alias:
            return self._alias == other_alias
        if self._name and other_name and (self._alias or other_alias):
            return self._alias == other_name or self._name == other_alias
        return self._name == other_name

    def __getitem__(self, index, **kwargs):
        """Access an item"""
        if self._nude:
            return self._items[0][index]
        for i, v in enumerate(self._items):
            if v == index:
                return self._items[i]
        if not 'default' in kwargs:
            raise IndexError(f"No such item {index}")
        return kwargs['default']

    def __call__(self, *args, **kwargs):
        """"""
        self.add(*args, **kwargs)
        return self

    def __hash__(self):
        """ Hash the lowercase string """
        return hash(self.name())


class NodesQL(GraphQLNode):
    """
    A simple 'nodes' wrapper
    """
    def __init__(self, _name, *args,
                 _nodes_alias=None, **kwargs):
        """
        Items in the '*args' list will be added to the 'nodes' element, and not
        to the top node.

        Parameters are passed to the top node.

        Parameters:
        :param _nodes_alias: Alias for the 'nodes' items. Nodes are called '{_name}_nodes'
            by default. Passing an empty string will remove the alias totally.
        :param _top: List of items to be added to the top node, instead of 'nodes'.
        """
        _alias = kwargs.pop('_alias') if '_alias' in kwargs else ''
        _node: GraphQLNode = kwargs.pop('_node') if '_node' in kwargs else False
        _top = kwargs.pop('_top') if '_top' in kwargs else []
        node_alias = _nodes_alias if _nodes_alias is not None else f'{_name}_nodes'
        if _node:
            if not isinstance(_node, GraphQLNode):
                raise ValueError('Nude items must be of type GraphQLNode')
            self.node = _node
            nude_node_name = self.node._alias if self.node._alias else self.node._name
            if _nodes_alias:
                nude_node_name = _nodes_alias
            elif nude_node_name:
                node_alias = nude_node_name
            else:
                node_alias = None
            if len(args) != 0:
                pass  # What to do if there are args? Ignore them looks safe
        else:
            node_alias = node_alias if node_alias or _nodes_alias else None
            self.node = GraphQLNode(node_alias, *args)
        self.alias_node = GraphQLNode('nodes', _node=self.node, _alias=node_alias)
        super().__init__(_name, *_top, self.alias_node, _alias=_alias, **kwargs)

    def add_to_nodes(self, *args):
        """
        Add items to the 'nodes' item
        """
        self.node._items.extend(list(args))


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
    def __init__(self, *args, **kwargs):
        args = list(args)
        if args and isinstance(args[0], FunctionType):
            getitems = args.pop(0)
            self._getitems = getitems
            self._name = getitems.__name__
            self.__doc__ = getitems.__doc__
            self._items = getitems(self)
        elif kwargs:
            self._getitems = None
            self._name = kwargs.pop('name')
            self.__doc__ = kwargs.pop('doc') if 'doc' in kwargs else ''
            self._items = kwargs.pop('items') if 'items' in kwargs else {}
        if kwargs or args:
            raise ValueError("Invalid parameters")

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
            self._derived_items, self._derived_params = node_items()
            self._derived_name = self._derived_params.pop('_name') \
                if '_name' in self._derived_params \
                else node_items.__name__[0].lower() + node_items.__name__[1:]
            super().__init__(self._derived_name,
                             *self._derived_items, **self._derived_params)
            self._constant = True

        def __call__(self, *args, **kwargs) -> GraphQLNode:
            """ Calling the decorated method will work as a constructor """
            for i, v in self._derived_params.items():
                if i not in kwargs:
                    kwargs[i] = v
            if '_node' in kwargs:  # Use node attributes if a node is provided
                return base_class(self._name, *args, **kwargs)
            return base_class(self._name, *self._derived_items, *args, **kwargs)

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
