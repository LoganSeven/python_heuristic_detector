# python_heuristic_detector.py
# -----------------------------------------------------------------------------
# @file     python_heuristic_detector.py
# @brief    Static Python code detector with optional wrapping and dangerous code checks.
#
# @author   LoganSeven
#
# -----------------------------------------------------------------------------

import json
import re
import logging
import ast
import textwrap
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Any

from qtpy.QtCore import QObject, Slot, Signal, QMutex, QMutexLocker, Property

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Two‑tier Python keywords
# -----------------------------------------------------------------------------
"""
@var STRONG_PY_KEYWORDS
Strong Python keywords that reliably indicate code if found in lines.
"""
STRONG_PY_KEYWORDS = {
    "def", "class", "import", "from", "if", "elif", "else", "try", "except",
    "with", "for", "while", "return", "print", "lambda", "yield", "assert",
    "nonlocal", "global", "raise", "async", "await", "pass", "continue", "break"
}

"""
@var WEAK_PY_KEYWORDS
Keywords too common in normal prose to be used as strong indicators of code.
"""
WEAK_PY_KEYWORDS = {"in", "is", "and", "or", "not"}

# -----------------------------------------------------------------------------
# Dangerous / security‑critical patterns
# -----------------------------------------------------------------------------
"""
@var _DANGEROUS_REGEX
Compiled regular expression identifying dangerous or security‑critical patterns.
Examples: dynamic code execution, rm -rf, certain file ops, etc.
"""
_DANGEROUS_REGEX = re.compile(
    r"""
    (?:
        # Shell / command execution
        \bos\.system\s*\(              |
        \bsubprocess\.(?:run|call|Popen) |
        # Dynamic code execution
        \beval\s*\(                    |
        \bexec\s*\(                    |
        # Destructive file operations
        \bshutil\.rmtree\s*\(           |
        (?:rm\s+-rf)                    |
        # Network / remote code loading
        \burllib\.(?:request|urlopen)   |
        \brequests?\.[A-Za-z_]+         |
        \bsocket\.[A-Za-z_]+            |
        # Pickle / marshal – arbitrary code execution vectors
        \bpickle\.(?:load|loads)        |
        \bmarshal\.(?:load|loads)
    )
""",
    re.IGNORECASE | re.VERBOSE
)


def _contains_dangerous_pattern(s: str) -> bool:
    """
    @brief Checks whether a string contains any known dangerous patterns.
    @param s The input string to search for dangerous patterns.
    @return True if a dangerous pattern is found, else False.
    """
    return bool(_DANGEROUS_REGEX.search(s))


# -----------------------------------------------------------------------------
# Security guard: 5MB max input size
# -----------------------------------------------------------------------------
"""
@var MAX_INPUT_SIZE
The maximum allowed size (in bytes) for any incoming text or JSON string.
"""
MAX_INPUT_SIZE = 5 * 1024 * 1024  # 5MB


# -----------------------------------------------------------------------------
# Helpers – code‑likeness, (un)escaping, comment stripping
# -----------------------------------------------------------------------------
def is_line_code_like(line: str) -> bool:
    """
    @brief Determines if a single line is likely Python code based on keywords/structure.
    @param line The line of text to inspect.
    @return True if the line is recognized as Python‑like, else False.
    """
    stripped = line.strip()
    if len(stripped) < 3:
        return False

    # Remove inline comments for checks
    if "#" in stripped:
        partial = stripped.split("#", 1)[0].rstrip()
        if len(partial) < 3:
            return False
        stripped = partial

    low = stripped.lower()
    # If it looks like JS or something else, skip
    if "function " in low or "console." in low:
        return False
    if any(ch in stripped for ch in "{};"):
        return False

    # Check typical Python block starters
    if re.match(r"^\s*(def|class|if|elif|else|try|except|with|for|while)\b.*:\s*$", stripped):
        return True

    # Check for strong Python keywords
    tokens = re.findall(r"[A-Za-z_]+", stripped)
    return any(tok in STRONG_PY_KEYWORDS for tok in tokens)


def strip_comments_from_block(block: str) -> str:
    """
    @brief Removes '#'‑based comments from a multi‑line code block.
    @param block The multi‑line string block.
    @return A new string with comments removed.
    """
    lines = []
    for ln in block.splitlines():
        ln = ln.rstrip("\r\n")
        if "#" in ln:
            ln = ln.split("#", 1)[0]
        lines.append(ln)
    return "\n".join(lines)


def _interpret_escaped_newlines(s: str) -> str:
    """
    @brief Converts literal '\\n' and '\\r' substrings into real newlines.
    @param s The input string with possibly escaped newlines.
    @return The same string but with actual newlines in place.
    """
    return s.replace("\\n", "\n").replace("\\r", "\r")


def _reescape_newlines(s: str) -> str:
    """
    @brief Re-escapes all newline/carriage returns back to '\\n' or '\\r'.
    @param s The input string containing real newlines.
    @return String with newlines re-escaped.
    """
    return s.replace("\r", "\\r").replace("\n", "\\n")


def might_contain_python_code(s: str) -> bool:
    """
    @brief Quick pre-check to see if a string might contain Python code.
    @param s The input string to test heuristics.
    @return True if we detect strong Python keywords or typical Python patterns; else False.
    """
    low = s.lower()
    # Quick skip if it explicitly looks like JS
    if "function " in low or "console." in low:
        tokens = re.findall(r"[A-Za-z_]+", low)
        if not any(t in STRONG_PY_KEYWORDS for t in tokens):
            return False

    # If any strong Python keyword is found, it's a possible code snippet
    tokens = re.findall(r"[A-Za-z_]+", low)
    return any(t in STRONG_PY_KEYWORDS for t in tokens)


# -----------------------------------------------------------------------------
# Main Class
# -----------------------------------------------------------------------------
class PythonHeuristicDetector(QObject):
    """
    @class PythonHeuristicDetector
    @brief A static Python code detector with optional <PythonCode> wrapping.

    This class provides methods to scan plain strings or JSON strings for code.
    If a snippet is considered "Python code" based on heuristics, it is optionally
    wrapped with <PythonCode>...</PythonCode>. Potentially dangerous code patterns
    (like os.system, etc.) are also flagged.
    """

    # -------------------------------------------------------------------------
    # Signals
    # -------------------------------------------------------------------------
    stat_json_too_low_signal = Signal(str)
    stat_str_too_low_signal = Signal(str)

    def __init__(self, parent=None, max_workers: int = 4):
        """
        @brief Constructor for PythonHeuristicDetector.
        @param parent Optional parent QObject.
        @param max_workers Max threads for parallel JSON list processing.
        """
        super().__init__(parent)
        self._mutex = QMutex()
        self._last_json_string = ""
        self._last_plain_string = ""
        self._stat_threshold: float = 70.0
        self._max_workers = max_workers
        self.python_detected_in_json = False
        self.python_detected_in_str = False
        self._dangerous_code_detected: bool = False

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    @property
    def dangerous_code_detected(self) -> bool:
        """
        @brief Indicates whether the last detection call encountered code flagged as dangerous.
        @return True if dangerous code was detected, else False.
        """
        with QMutexLocker(self._mutex):
            return self._dangerous_code_detected

    @dangerous_code_detected.setter
    def dangerous_code_detected(self, val: bool):
        """
        @brief Sets the dangerous_code_detected flag.
        @param val The new boolean value for this flag.
        """
        with QMutexLocker(self._mutex):
            self._dangerous_code_detected = val

    @Property(float)
    def stat_threshold(self) -> float:
        """
        @brief Accessor for the detection threshold used when wrapping code blocks.
        Blocks with a confidence below this threshold cause reversion to the original text/JSON.
        @return The current numeric threshold.
        """
        with QMutexLocker(self._mutex):
            return self._stat_threshold

    @stat_threshold.setter
    def stat_threshold(self, value: float):
        """
        @brief Setter for the detection threshold.
        @param value The desired threshold (clamped to [0.0, 100.0]).
        """
        with QMutexLocker(self._mutex):
            self._stat_threshold = max(0.0, min(100.0, value))

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------
    def _form_code_blocks(self, text: str) -> List[Tuple[int, int]]:
        """
        Identify code blocks by grouping consecutive lines, once we decide
        "we are inside code." A line can be considered inside code if either
        it is code-like by itself, or it is blank/indented following a code-like line.
        We stop the block at a clearly non-code line with no indentation.
        """
        lines = text.splitlines(keepends=True)
        blocks = []
        n = len(lines)

        in_code_block = False
        block_start = 0

        for i in range(n):
            line = lines[i]
            stripped = line.strip()

            if in_code_block:
                # If we're already in a code block, check if we stay in it
                if (
                    is_line_code_like(line)
                    or stripped == ""                     # blank line => still part of code
                    or line.startswith((" ", "\t"))       # indentation => code continuation
                ):
                    # Continue inside the same code block
                    continue
                else:
                    # We reached a line that is definitely not code-like
                    # and not blank or indented => close block up to previous line
                    blocks.append((block_start, i - 1))
                    in_code_block = False
            else:
                # Not in a code block; check if this line starts one
                if is_line_code_like(line):
                    in_code_block = True
                    block_start = i
                else:
                    # Still outside code
                    continue

        # If we end the file while still in a code block, close it
        if in_code_block:
            blocks.append((block_start, n - 1))

        return blocks

    def _calculate_confidence_for_block(self, block: str) -> float:
        """
        @brief Evaluates how confidently 'block' qualifies as valid Python code using AST parsing.
        @param block The multi‑line code block (already singled out).
        @return A float confidence score in [0..100]. Higher means more likely Python code.
        """
        stripped = strip_comments_from_block(block)
        code_lines = [ln for ln in stripped.splitlines() if ln.strip()]
        if not code_lines:
            return 0.0

        dedented = textwrap.dedent("\n".join(code_lines))
        try:
            ast.parse(dedented)
            # If it parses, multi-line is quite certain (100), single-line is moderate (80).
            return 80.0 if len(code_lines) == 1 else 100.0
        except (SyntaxError, IndentationError):
            tokens = re.findall(r"[A-Za-z_]+", stripped)
            if any(t in STRONG_PY_KEYWORDS for t in tokens):
                return 80.0 if len(code_lines) == 1 else 100.0
            return 0.0

    def _wrap_code_blocks_in_text(self,
                                  text: str,
                                  start_tag: str,
                                  end_tag: str) -> Tuple[str, float, bool]:
        """
        @brief Scans a plain text string for code blocks, optionally wrapping them in
               <start_tag> / <end_tag>.
        @param text The input text to analyze.
        @param start_tag The tag to prepend to recognized code blocks.
        @param end_tag The tag to append to recognized code blocks.
        @return A tuple: (possibly modified text, average confidence, did_wrap_any_code)
        """
        blocks = self._form_code_blocks(text)

        if not blocks:
            # Even if not recognized as code, we still check for dangerous patterns
            if _contains_dangerous_pattern(text):
                self.dangerous_code_detected = True
            return text, 0.0, False

        with QMutexLocker(self._mutex):
            threshold = self._stat_threshold

        lines = text.splitlines(keepends=True)
        out = []
        confs = []
        last = 0
        did_wrap = False

        for start_i, end_i in blocks:
            # Append everything before this block unmodified
            if start_i > last:
                prefix = "".join(lines[last:start_i])
                if _contains_dangerous_pattern(prefix):
                    self.dangerous_code_detected = True
                out.append(prefix)

            # Evaluate and handle the block
            block_str = "".join(lines[start_i:end_i + 1])
            conf = self._calculate_confidence_for_block(block_str)
            confs.append(conf)

            if _contains_dangerous_pattern(block_str):
                self.dangerous_code_detected = True

            if conf >= threshold:
                out.append(f"{start_tag}{block_str}{end_tag}")
                did_wrap = True
            else:
                out.append(block_str)

            last = end_i + 1

        # Append any trailing lines after the last block
        if last < len(lines):
            tail = "".join(lines[last:])
            if _contains_dangerous_pattern(tail):
                self.dangerous_code_detected = True
            out.append(tail)

        avg_conf = sum(confs) / len(confs) if confs else 0.0

        # If we did wrap but the average conf is below threshold, revert to original
        if did_wrap and avg_conf < threshold:
            return text, avg_conf, False

        return "".join(out), avg_conf, did_wrap

    def _process_string_field(self,
                              original: str,
                              start_tag: str,
                              end_tag: str) -> Tuple[str, List[float], bool, bool]:
        """
        @brief Processes a string field extracted from JSON, scanning for Python code & possibly wrapping.
        @param original The original string as found in the JSON.
        @param start_tag Tag inserted before recognized code blocks.
        @param end_tag Tag inserted after recognized code blocks.
        @return (modified_string, [list_of_confidences], did_wrap, changed)
        """
        if len(original.strip()) < 5:
            return original, [], False, False

        unescaped = _interpret_escaped_newlines(original)
        if not might_contain_python_code(unescaped) and not _contains_dangerous_pattern(unescaped):
            return original, [], False, False

        if _contains_dangerous_pattern(unescaped):
            self.dangerous_code_detected = True

        wrapped, conf, did_wrap = self._wrap_code_blocks_in_text(unescaped, start_tag, end_tag)
        changed = False
        if did_wrap:
            reescaped = _reescape_newlines(wrapped)
            changed = (reescaped != original)
            return reescaped, [conf], True, changed

        return original, [conf], False, changed

    def _wrap_code_in_json(self,
                           obj: Any,
                           start_tag: str,
                           end_tag: str,
                           parallel: bool) -> Tuple[Any, List[float], bool, bool]:
        """
        @brief Recursively descends through parsed JSON (dict, list, or scalars)
               and wraps code blocks in any encountered strings.
        @param obj The current JSON object (dict, list, string, or other).
        @param start_tag Tag inserted before recognized code blocks.
        @param end_tag Tag inserted after recognized code blocks.
        @param parallel Whether to process list items in parallel threads.
        @return (new_obj, list_of_confidences, did_wrap_any, changed_any)
        """
        confs = []
        did_wrap_any = False
        changed_any = False

        if isinstance(obj, dict):
            new_dict = {}
            for k, v in obj.items():
                nv, c, dw, ch = self._wrap_code_in_json(v, start_tag, end_tag, parallel)
                new_dict[k] = nv
                confs.extend(c)
                did_wrap_any |= dw
                changed_any |= ch
            return new_dict, confs, did_wrap_any, changed_any

        elif isinstance(obj, list):
            if parallel and len(obj) > 1:
                with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
                    results = list(pool.map(
                        lambda item: self._wrap_code_in_json(item, start_tag, end_tag, parallel),
                        obj
                    ))
                new_list = []
                for (nv, c, dw, ch) in results:
                    new_list.append(nv)
                    confs.extend(c)
                    did_wrap_any |= dw
                    changed_any |= ch
                return new_list, confs, did_wrap_any, changed_any
            else:
                new_list = []
                for it in obj:
                    nv, c, dw, ch = self._wrap_code_in_json(it, start_tag, end_tag, parallel)
                    new_list.append(nv)
                    confs.extend(c)
                    did_wrap_any |= dw
                    changed_any |= ch
                return new_list, confs, did_wrap_any, changed_any

        elif isinstance(obj, str):
            return self._process_string_field(obj, start_tag, end_tag)

        else:
            return obj, confs, False, False

    # -------------------------------------------------------------------------
    # Public Slots / API
    # -------------------------------------------------------------------------
    @Slot(str, str, str, bool, bool, result=str)
    def detectPythonCodeInJson(self,
                               input_string: str,
                               start_tag: str = "<PythonCode>",
                               end_tag: str = "</PythonCode>",
                               verbose: bool = False,
                               parallel: bool = False) -> str:
        """
        @brief Parses a JSON string, scans all string fields for Python code,
               optionally wraps recognized code blocks, then returns the JSON re-serialized.
        @param input_string The JSON string to process.
        @param start_tag Tag for wrapping recognized code.
        @param end_tag Closing tag for recognized code.
        @param verbose If True, extra debug info is logged.
        @param parallel If True, list items are processed in parallel threads.
        @return Possibly modified JSON string. If wrapping is reverted, returns the original input.
        @exception json.JSONDecodeError If the input_string is not valid JSON.
        """
        with QMutexLocker(self._mutex):
            self._dangerous_code_detected = False
            self._last_json_string = input_string

        if len(input_string.encode("utf-8")) > MAX_INPUT_SIZE:
            logger.warning("Input exceeds 5MB – returning verbatim.")
            self.python_detected_in_json = False
            return input_string

        try:
            data = json.loads(input_string)
        except json.JSONDecodeError as e:
            if verbose:
                logger.debug(f"[JSON parse error] {e}")
            raise

        new_data, confs, did_wrap, changed = self._wrap_code_in_json(
            data, start_tag, end_tag, parallel
        )
        avg_conf = sum(confs) / len(confs) if confs else 0.0

        with QMutexLocker(self._mutex):
            threshold = self._stat_threshold

        if verbose:
            logger.debug(
                f"[detectPythonCodeInJson] avg_conf={avg_conf:.1f}, threshold={threshold}, "
                f"did_wrap={did_wrap}, changed={changed}, dangerous={self._dangerous_code_detected}"
            )

        # If code was wrapped but average confidence is below threshold, revert
        if did_wrap and avg_conf < threshold:
            self.stat_json_too_low_signal.emit(self._last_json_string)
            self.python_detected_in_json = False
            return self._last_json_string

        # If nothing actually changed, no code was wrapped
        if not changed:
            self.python_detected_in_json = False
            return input_string

        self.python_detected_in_json = True
        return json.dumps(new_data, ensure_ascii=False)

    @Slot(str, str, str, bool, result=str)
    def detectPythonInString(self,
                             input_string: str,
                             start_tag: str = "<PythonCode>\n",
                             end_tag: str = "</PythonCode>\n",
                             verbose: bool = False) -> str:
        """
        @brief Scans a plain string for Python code, optionally wraps recognized blocks in
               <start_tag>...</end_tag>, and returns the modified text.
        @param input_string The raw text to analyze.
        @param start_tag Tag for wrapping recognized code blocks.
        @param end_tag Closing tag for recognized code blocks.
        @param verbose If True, additional debug info is logged.
        @return Possibly modified text. If code blocks do not meet threshold, returns the original.
        """
        with QMutexLocker(self._mutex):
            self._dangerous_code_detected = False
            self._last_plain_string = input_string

        if len(input_string.encode("utf-8")) > MAX_INPUT_SIZE:
            logger.warning("Input exceeds 5MB – returning verbatim.")
            self.python_detected_in_str = False
            return input_string

        wrapped, conf, did_wrap = self._wrap_code_blocks_in_text(input_string, start_tag, end_tag)

        with QMutexLocker(self._mutex):
            threshold = self._stat_threshold

        if verbose:
            logger.debug(
                f"[detectPythonInString] conf={conf:.1f}, threshold={threshold}, "
                f"did_wrap={did_wrap}, dangerous={self._dangerous_code_detected}"
            )

        if did_wrap and conf < threshold:
            self.stat_str_too_low_signal.emit(self._last_plain_string)
            self.python_detected_in_str = False
            return self._last_plain_string

        if not did_wrap:
            # Possibly still dangerous code
            if _contains_dangerous_pattern(input_string):
                self.dangerous_code_detected = True
            self.python_detected_in_str = False
            return input_string

        self.python_detected_in_str = True
        return wrapped
