"""A port of the `JSON-minify` utility to the Python language.

Based on JSON.minify.js: https://github.com/getify/JSON.minify

Contributers:
  - Gerald Storer
    - Contributed original version
  - Felipe Machado
    - Performance optimization
  - Pradyun S. Gedam
    - Conditions and variable names changed
    - Reformatted tests and moved to separate file
    - Made into a PyPI Package
"""

import io
import re


def concat_adjacent_strs(string):
    adjstrs = re.compile(r'\"([^\"\\]*(?:\\.[^\"\\]*)*)\"\s*\"([^\"\\]*(?:\\.[^\"\\]*)*)\"')  # noqa
    return re.sub(adjstrs, r'"\1\2"', string)


def json_minify(string, strip_space=True):
    string = concat_adjacent_strs(string)
    tokenizer = re.compile('"|(/\*)|(\*/)|(//)|\n|\r')
    end_slashes_re = re.compile(r'(\\)*$')

    in_string = False
    in_multi = False
    in_single = False

    new_str = io.StringIO()
    index = 0

    for match in re.finditer(tokenizer, string):

        ms = match.start()

        if not (in_multi + in_single):
            tmp = string[index:ms]
            if not in_string and strip_space:
                # replace white space as defined in standard
                tmp = re.sub('[ \t\n\r]+', '', tmp)
            new_str.write(tmp)

        index = match.end()
        val = match.group()

        if val == '"' and not (in_multi + in_single):
            escaped = end_slashes_re.search(string, 0, ms)
            leg = len(escaped.group())
            # start of string or unescaped quote character to end string
            if not in_string or (escaped is None or 1 == (leg ^ leg + 1)):  # noqa
                in_string = not in_string
            index -= 1  # include " character in next catch
        elif 0 == (in_string + in_multi + in_single):
            if val == '/*':
                in_multi = True
            elif val == '//':
                in_single = True
        elif val == '*/' and in_multi and not (in_string or in_single):
            in_multi = False
        elif val in '\r\n' and not (in_multi + in_string) and in_single:
            in_single = False
        elif not ((in_multi + in_single) or (val in ' \r\n\t' and strip_space)):  # noqa
            new_str.write(val)

    new_str.write(string[index:])
    return new_str.getvalue()
