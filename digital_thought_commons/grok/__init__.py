import glob
import os
import pathlib

try:
    import regex as re
except ImportError as e:
    # If you import re, grok_match can't handle regular expression containing atomic group(?>)
    import re


def load_patterns(path):
    loaded_patterns = {}
    for file in glob.glob('{}/*'.format(path), recursive=True):
        if not os.path.isdir(file):
            with open(file, 'r', encoding="UTF-8") as pattern_file:
                for line in pattern_file:
                    if len(line.strip()) == 0 or line.startswith('#'):
                        continue

                    separator = line.find(' ')
                    name = line[:separator]
                    pattern = line[separator:].strip()
                    loaded_patterns[name] = pattern

    return loaded_patterns


patterns_folder = "{}/../_resources/grok".format(str(pathlib.Path(__file__).parent.absolute()))
patterns = load_patterns(path=patterns_folder)


class Grok:

    def __init__(self, custom_patterns_dir=None, custom_patterns=None, full_match=False):
        self.patterns = patterns
        self.full_match = full_match
        if custom_patterns_dir is not None:
            self.patterns.update(load_patterns(custom_patterns_dir))
        if custom_patterns is not None:
            self.patterns.update(custom_patterns)

    def __load_pattern(self, pattern):
        mapper = {}
        while True:
            match = re.findall(r'%{(\w+):(\w+):(\w+)}', pattern)
            for instance in match:
                mapper[instance[1]] = instance[2]

            pattern = re.sub(r'%{(\w+):(\w+)(?::\w+)?}',
                             lambda m: "(?P<" + m.group(2) + ">" + self.patterns[m.group(1)] + ")",
                             pattern)

            pattern = re.sub(r'%{(\w+)}',
                             lambda m: "(" + self.patterns[m.group(1)] + ")",
                             pattern)

            if re.search('%{\w+(:\w+)?}', pattern) is None:
                break

        return re.compile(pattern), mapper

    def grok(self, text, search_patterns, break_on_match=False):
        objects = []
        for search_pattern in search_patterns:
            regex_obj, mapper = self.__load_pattern(search_pattern)
            match_obj = None
            if self.full_match:
                match_obj = regex_obj.fullmatch(text)
            else:
                match_obj = regex_obj.search(text)

            if match_obj is not None:
                matches = match_obj.groupdict()
                for key, match in matches.items():
                    try:
                        if mapper[key] == 'int':
                            matches[key] = int(match)
                        if mapper[key] == 'float':
                            matches[key] = float(match)
                    except (TypeError, KeyError) as e:
                        pass
                objects.append(matches)
                if break_on_match and len(objects) > 0:
                    return objects

        return objects
