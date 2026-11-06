"""Ten small coding tasks for the local-model benchmark (plan L, task L7).

Each task: `prompt` (what the model is told), `stub` (the starting impl.py), `check` (check.py, protected, exit 0 = pass),
`reference` (a correct solution, proves the check can pass) and `naive` (a plausible wrong solution, proves the check can fail).
Several checks deliberately test TYPES and edge cases, because that is where small models slip (measured: int parsed as float).
"""

TASKS = [
    {
        "id": "parse_score",
        "prompt": "Implement parse_score(s: str) -> dict in impl.py. It parses 'key=value,key=value'. A value is an int when it looks like an integer, otherwise a float. A part without '=' raises ValueError.",
        "stub": "def parse_score(s):\n    raise NotImplementedError\n",
        "check": '''from impl import parse_score
r = parse_score("a=1,b=2.5")
assert r == {"a": 1, "b": 2.5}
assert type(r["a"]) is int, "a must be int"
assert type(r["b"]) is float, "b must be float"
assert type(parse_score("n=-7")["n"]) is int
try:
    parse_score("nokey")
except ValueError:
    pass
else:
    raise SystemExit("ValueError expected")
''',
        "reference": '''def parse_score(s):
    out = {}
    for part in s.split(","):
        if "=" not in part:
            raise ValueError("missing =")
        k, v = part.split("=", 1)
        try:
            out[k] = int(v)
        except ValueError:
            out[k] = float(v)
    return out
''',
        "naive": '''def parse_score(s):
    out = {}
    for part in s.split(","):
        if "=" not in part:
            raise ValueError("missing =")
        k, v = part.split("=", 1)
        out[k] = float(v)
    return out
''',
    },
    {
        "id": "slugify",
        "prompt": "Implement slugify(text: str) -> str in impl.py. Lowercase the text, replace every run of characters that are not a-z or 0-9 by a single '-', and strip '-' from both ends. The empty string gives the empty string.",
        "stub": "def slugify(text):\n    raise NotImplementedError\n",
        "check": '''from impl import slugify
assert slugify("Hello, World!") == "hello-world"
assert slugify("  A   B  ") == "a-b"
assert slugify("") == ""
assert slugify("---x---") == "x"
assert slugify("C3PO & R2-D2") == "c3po-r2-d2"
''',
        "reference": '''import re


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
''',
        "naive": '''def slugify(text):
    return text.lower().replace(" ", "-")
''',
    },
    {
        "id": "fizzbuzz",
        "prompt": "Implement fizzbuzz(n: int) -> list in impl.py. It returns the strings for 1..n: 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, 'FizzBuzz' for both, otherwise the number as a string. fizzbuzz(0) is an empty list.",
        "stub": "def fizzbuzz(n):\n    raise NotImplementedError\n",
        "check": '''from impl import fizzbuzz
r = fizzbuzz(15)
assert len(r) == 15 and r[0] == "1" and r[2] == "Fizz" and r[4] == "Buzz" and r[14] == "FizzBuzz"
assert all(type(x) is str for x in r), "every item must be a str"
assert fizzbuzz(0) == []
''',
        "reference": '''def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out
''',
        "naive": '''def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(i)
    return out
''',
    },
    {
        "id": "is_palindrome",
        "prompt": "Implement is_palindrome(s: str) -> bool in impl.py. Ignore case and every character that is not a letter or digit. The empty string is a palindrome.",
        "stub": "def is_palindrome(s):\n    raise NotImplementedError\n",
        "check": '''from impl import is_palindrome
assert is_palindrome("A man, a plan, a canal: Panama") is True
assert is_palindrome("race a car") is False
assert is_palindrome("") is True
assert is_palindrome("0P") is False
assert is_palindrome("No 'x' in Nixon") is True
''',
        "reference": '''def is_palindrome(s):
    t = [c.lower() for c in s if c.isalnum()]
    return t == t[::-1]
''',
        "naive": '''def is_palindrome(s):
    return s == s[::-1]
''',
    },
    {
        "id": "merge_intervals",
        "prompt": "Implement merge_intervals(intervals: list) -> list in impl.py. Each interval is [start, end]. Return the merged intervals sorted by start; intervals that overlap or touch (end == next start) are merged. Do not modify the input list. An empty input gives an empty list.",
        "stub": "def merge_intervals(intervals):\n    raise NotImplementedError\n",
        "check": '''from impl import merge_intervals
data = [[8, 10], [1, 3], [2, 6], [15, 18], [6, 7]]
copy = [list(x) for x in data]
assert merge_intervals(data) == [[1, 7], [8, 10], [15, 18]]
assert data == copy, "input must not be modified"
assert merge_intervals([]) == []
assert merge_intervals([[1, 2], [2, 3]]) == [[1, 3]]
assert merge_intervals([[5, 6]]) == [[5, 6]]
''',
        "reference": '''def merge_intervals(intervals):
    out = []
    for start, end in sorted(([a, b] for a, b in intervals), key=lambda x: x[0]):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out
''',
        "naive": '''def merge_intervals(intervals):
    out = []
    for start, end in intervals:
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out
''',
    },
    {
        "id": "roman_to_int",
        "prompt": "Implement roman_to_int(s: str) -> int in impl.py for uppercase roman numerals with the usual subtractive rule (IV = 4, IX = 9, XL, XC, CD, CM). An empty string or any character that is not one of IVXLCDM raises ValueError.",
        "stub": "def roman_to_int(s):\n    raise NotImplementedError\n",
        "check": '''from impl import roman_to_int
assert roman_to_int("XIV") == 14
assert roman_to_int("MCMXCIV") == 1994
assert roman_to_int("IX") == 9
assert roman_to_int("III") == 3
for bad in ("", "ABC", "XIZ", "iv"):
    try:
        roman_to_int(bad)
    except ValueError:
        pass
    else:
        raise SystemExit("ValueError expected for " + repr(bad))
''',
        "reference": '''VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(s):
    if not s or any(c not in VALUES for c in s):
        raise ValueError("invalid roman numeral")
    total = 0
    for i, c in enumerate(s):
        v = VALUES[c]
        if i + 1 < len(s) and VALUES[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total
''',
        "naive": '''VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(s):
    return sum(VALUES[c] for c in s)
''',
    },
    {
        "id": "flatten",
        "prompt": "Implement flatten(nested: list) -> list in impl.py. It flattens arbitrarily nested lists into one flat list, keeping order. Strings are single items and must not be split into characters. flatten([]) is [].",
        "stub": "def flatten(nested):\n    raise NotImplementedError\n",
        "check": '''from impl import flatten
assert flatten([1, [2, [3, "ab"]], []]) == [1, 2, 3, "ab"]
assert flatten([]) == []
assert flatten([[["x"]]]) == ["x"]
assert flatten(["hello", ["world"]]) == ["hello", "world"]
''',
        "reference": '''def flatten(nested):
    out = []
    for x in nested:
        if isinstance(x, list):
            out.extend(flatten(x))
        else:
            out.append(x)
    return out
''',
        "naive": '''def flatten(nested):
    out = []
    for x in nested:
        try:
            out.extend(flatten(x))
        except TypeError:
            out.append(x)
    return out
''',
    },
    {
        "id": "word_count",
        "prompt": "Implement word_count(text: str) -> dict in impl.py. Words are runs of letters and digits; counting is case-insensitive and the keys are lowercase. Punctuation is not part of a word. The empty string gives {}.",
        "stub": "def word_count(text):\n    raise NotImplementedError\n",
        "check": '''from impl import word_count
assert word_count("The the, THE!") == {"the": 3}
assert word_count("a b a c, b a.") == {"a": 3, "b": 2, "c": 1}
assert word_count("") == {}
assert word_count("R2D2 r2d2") == {"r2d2": 2}
r = word_count("x x")
assert type(r["x"]) is int
''',
        "reference": '''import re


def word_count(text):
    out = {}
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        out[w] = out.get(w, 0) + 1
    return out
''',
        "naive": '''def word_count(text):
    out = {}
    for w in text.lower().split():
        out[w] = out.get(w, 0) + 1
    return out
''',
    },
    {
        "id": "clamp",
        "prompt": "Implement clamp(x, lo, hi) in impl.py. It returns lo if x < lo, hi if x > hi, otherwise x itself (an int stays an int, a float stays a float). If lo > hi it raises ValueError.",
        "stub": "def clamp(x, lo, hi):\n    raise NotImplementedError\n",
        "check": '''from impl import clamp
assert clamp(15, 1, 10) == 10
assert clamp(-1, 1, 10) == 1
r = clamp(5, 1, 10)
assert r == 5 and type(r) is int
r = clamp(2.5, 1, 10)
assert r == 2.5 and type(r) is float
try:
    clamp(1, 2, 1)
except ValueError:
    pass
else:
    raise SystemExit("ValueError expected")
''',
        "reference": '''def clamp(x, lo, hi):
    if lo > hi:
        raise ValueError("lo must not exceed hi")
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
''',
        "naive": '''def clamp(x, lo, hi):
    return max(lo, min(x, hi))
''',
    },
    {
        "id": "chunk",
        "prompt": "Implement chunk(items: list, n: int) -> list in impl.py. It splits items into consecutive lists of length n; the last one may be shorter. n <= 0 raises ValueError. An empty list gives []. Do not modify the input.",
        "stub": "def chunk(items, n):\n    raise NotImplementedError\n",
        "check": '''from impl import chunk
data = [1, 2, 3, 4, 5]
assert chunk(data, 2) == [[1, 2], [3, 4], [5]]
assert data == [1, 2, 3, 4, 5]
assert chunk([], 3) == []
assert chunk([1, 2], 5) == [[1, 2]]
for bad in (0, -1):
    try:
        chunk(data, bad)
    except ValueError:
        pass
    else:
        raise SystemExit("ValueError expected for n=" + str(bad))
''',
        "reference": '''def chunk(items, n):
    if n <= 0:
        raise ValueError("n must be positive")
    return [list(items[i : i + n]) for i in range(0, len(items), n)]
''',
        "naive": '''def chunk(items, n):
    return [list(items[i : i + n]) for i in range(0, len(items), n)]
''',
    },
]
