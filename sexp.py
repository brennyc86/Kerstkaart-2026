"""Minimale S-expression lezer/schrijver voor KiCad-bestanden."""
import re

class Q(str):
    """tekst die tussen aanhalingstekens hoort"""

def parse(text):
    tok = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    pos = 0
    def rd():
        nonlocal pos
        t = tok[pos]; pos += 1
        if t == '(':
            lst = []
            while tok[pos] != ')': lst.append(rd())
            pos += 1
            return lst
        if t.startswith('"'): return Q(t[1:-1].replace('\\"', '"'))
        return t
    return rd()

def dump(n):
    if isinstance(n, list): return '(' + ' '.join(dump(c) for c in n) + ')'
    if isinstance(n, Q): return '"' + str(n).replace('"', '\\"') + '"'
    s = str(n)
    if s == '' or re.search(r'[\s()"]', s): return '"' + s + '"'
    return s
