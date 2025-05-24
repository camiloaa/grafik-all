"""
Parse GraphQL query
"""
import re
from typing import Optional
from .graphql import GraphQLNode, GraphQLEnum


SYNTAX_TOKEN = ['(', ')', '{', '}', ',', ':']

# Reversed regex
# Parser works on a reversed string.
token_re = re.compile(r"\w+")
symbol_re = re.compile(r"[{}\[\]]")
string_re = re.compile(r'\"('                          # Open with double quotes
                       r'[\"\\/bfnrt]\\'               # Escaped chars
                       r'|u[0-9A-Fa-f]{4}\\'           # Escaped unicode
                       r'|[^\"\\\n\r\u2028\u2029]'     # Anything that is not new-line or quotes
                       r')*\"')                        # Quotes
# Forward regex
identifier_re = re.compile(r"\w+(:\s*\w+){0,1}")


def sanitize_query(query: str):
    """Remove new lines and training spaces"""
    control_char_re = re.compile(r'[\x00-\x1f\x7f-\x9f]')
    lines = [control_char_re.sub('', x.strip()) for x in query.split("\n")]
    return " ".join(lines)[::-1]


def _get_stripped(text: str, to_remove: int):
    """Strip text and return how many characters were removed"""
    lenght = len(text)
    text = text[to_remove:].strip()
    return lenght - len(text), text


def _get_next_token(query: str):
    """Get next item name and alias or syntax token"""
    removed, query = _get_stripped(query, 0)
    if not query:
        return '', removed, query
    # alphanumeric token
    token = token_re.match(query)
    if token:
        token = token.group()
        s, query = _get_stripped(query, len(token))
        removed += s
        return f"{token[::-1]}", removed, query
    # string
    token = string_re.match(query)
    if token:
        token = token.group()
        s, query = _get_stripped(query, len(token))
        removed += s
        return f"{token[::-1]}", removed, query

    # Default token is next char
    r = query[0]
    s, query = _get_stripped(query, 1)
    removed += s
    return r, removed, query


def _parse_params(query: str, closing: str, position: int, env: dict):
    """Get graphql parameters for the given depth"""
    params = {}
    value = None
    waiting_value = True
    token, removed, query = _get_next_token(query)
    while token:
        #print(token)
        position -= removed
        if token == closing:
            return params, position, query
        elif waiting_value and token == '}':
            items, position, query = _parse_params(query, '{', position, env)
            waiting_value = False
            value = GraphQLNode('', **items)
        elif token in ['{', '(', ')']:
            raise SyntaxError(f"Unmatched token '{token}' in position {position}")
        elif token == ",":  # Commas are optional
            if not waiting_value:
                raise SyntaxError(f"Invalid separator ',' in position {position}")
        elif token == ":":
            if waiting_value:
                raise SyntaxError(f"Invalid separator ':' in position {position}")
        elif token == "$":
            if waiting_value:
                raise SyntaxError(f"Invalid separator ':' in position {position}")
            waiting_value = False
        elif waiting_value and token.startswith('"'):
            value = token.strip('"')  # String value
            if value.startswith('$'):
                value = env.get(value[1:], '')
            waiting_value = False
        elif waiting_value and token.isnumeric():
            value = int(token)
            waiting_value = False
        elif token.isidentifier():
            if waiting_value:
                if query.startswith("$"):
                    tmp = env.get(token, None)
                    if not tmp:
                        raise ValueError(f"Environment variable ${token} is not defined")
                    token = tmp
                if token == "true":
                    value = True
                elif token == "false":
                    value = False
                else:
                    value = GraphQLEnum(name=token)  # Enum
                waiting_value = False
            else:
                params[token] = value  # Identifier
                waiting_value = True
        else:
            raise SyntaxError(f"Invalid identifier {token} in position {position}")
        token, removed, query = _get_next_token(query)
    if closing or waiting_value:
        raise SyntaxError(f"Missing token '{closing}' in position {position}")
    return params, position, query


def _get_graphql_nodes(query: str, closing: str, position: int, env: dict):
    """Get graphql nodes for the given depth"""
    items = []
    params = {}
    nodes = []
    prev_token = ''
    token, removed, query = _get_next_token(query)
    while token:
        position -= removed
        if token == ',':  # Commas are optional
            if prev_token in SYNTAX_TOKEN:
                raise SyntaxError(f"Invalid identifier {token} in position {position}")
        elif token == '}':
            items, position, query = _get_graphql_nodes(query, '{', position, env)
        elif token == ')':
            params, position, query = _parse_params(query, '(', position, env)
        elif token == closing:
            return nodes, position, query
        elif token in ['{', '(']:
            raise SyntaxError(f"Unmatched token '{token}' in position {position}")
        elif token.isidentifier():
            if query.startswith(':'):  # There is an alias for this identifier
                s, query = _get_stripped(query, 1)
                position = position - s
                alias, removed, query = _get_next_token(query)
                if not alias:
                    raise SyntaxError(f"Invalid separator ':' in position {position}")
                token = f"{alias}: {token}"
            nodes.insert(0, GraphQLNode(token, *items, **params))
            items = []
            params = {}
        else:
            raise SyntaxError(f"Invalid identifier {token} in position {position}")
        prev_token = token
        token, removed, query = _get_next_token(query)
    if closing:
        raise SyntaxError(f"Missing token '{closing}' in position {position}")
    if items or params:
        #print(items, f"'{token}'", params)
        nodes.insert(0, GraphQLNode('', *items, **params))
    return nodes, position, query


def string_to_graphql(query: str, env: Optional[dict] = None):
    """
    Parse a graphql query and transform it into a GraphqlNode.
    All generated items are of type GraphQLNode to make it easier to further modify the
    resulting nodes.

    :param str query: The graphql query to be parsed
    :param dict env: Dictionary to be use as environment to parse $VAR symbols
    :return: List of parsed nodes
    :raises SyntaxError: If a syntax error is found
    :raises ValueError: If the requested environment variable doesn't exist
    """
    env = env if env else {}
    query = sanitize_query(query)
    position = len(query)
    nodes, *_ = _get_graphql_nodes(query, '', position, env)
    return nodes
