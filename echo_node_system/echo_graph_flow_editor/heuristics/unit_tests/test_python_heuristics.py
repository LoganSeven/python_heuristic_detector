import os
import sys
import unittest
import json

# Adjust the system path so that the module can be found.
# Our project structure is assumed to be:
# <project_root>/echo_node_system/echo_graph_flow_editor/heuristics/python_heuristic_detector.py
#
# Since this test file is located at:
# <project_root>/echo_node_system/echo_graph_flow_editor/heuristics/unit_tests/test_python_heuristics.py
# we add the project root (four levels up) to sys.path.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import the module using its package path.
from echo_node_system.echo_graph_flow_editor.heuristics.python_heuristic_detector import PythonHeuristicDetector


class TestPythonHeuristicDetector(unittest.TestCase):
    def setUp(self):
        """
        Create a new instance of the PythonHeuristicDetector before each test.
        Adjust the threshold so that moderately-likely code gets wrapped,
        which helps test partial parsing and line-by-line detection.
        """
        self.detector = PythonHeuristicDetector()
        # Lower threshold for testing purposes; adjust as needed.
        self.detector.stat_threshold = 40.0

    ########################################################################
    # Non malicious tests (raw str)
    ########################################################################
    def test_pure_text_no_code(self):
        """
        A test with absolutely no Python code or suspicious lines.
        Should remain unmodified (no <PythonCode> tags).
        """
        text = "Hello world. This is purely a normal sentence. 12345? Yes!"
        result = self.detector.detectPythonInString(text, verbose=False)
        self.assertEqual(text, result, "Pure text with no code must remain unchanged.")
        # Check that the dangerous_code_detected flag is False
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_pure_text_no_code: SUCCESS")

    def test_javascript_snippet(self):
        """
        A snippet containing JavaScript code. Should NOT be wrapped as Python.
        """
        js_code = (
            "function greet(name) {\n"
            "    console.log('Hello, ' + name);\n"
            "}\n"
        )
        result = self.detector.detectPythonInString(js_code, verbose=False)
        # We do NOT expect <PythonCode> tags.
        self.assertEqual(js_code, result, "JavaScript snippet should remain unchanged.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_javascript_snippet: SUCCESS")

    def test_no_code_in_string(self):
        """
        Verify that a string with no Python code remains unmodified.
        """
        text = "Just a normal sentence, no code here at all."
        result = self.detector.detectPythonInString(text, verbose=False)
        self.assertEqual(text, result, "String with no code should remain unchanged.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_no_code_in_string: SUCCESS")

    def test_simple_code_in_string(self):
        """
        Verify that a simple code snippet is detected and wrapped.
        """
        text = "Here is a code snippet:\ndef say_hello():\n    print('Hello')\n"
        result = self.detector.detectPythonInString(text, verbose=False)
        self.assertIn("<PythonCode>", result, "Expected code to be wrapped in <PythonCode>.")
        self.assertIn("</PythonCode>", result, "Expected code to be closed with </PythonCode>.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_simple_code_in_string: SUCCESS")

    def test_partial_syntax_error_code(self):
        """
        Use a code snippet with a minor error to verify that partial AST parsing
        salvages valid code. The invalid call 'prnt' should be skipped or not
        lower the block confidence too far.
        """
        text = (
            "Some text...\n"
            "def greet(name):\n"
            "    print(f'Hello, {name}')\n"
            "prnt('Oops')  # This line is erroneous\n"
            "for i in range(2):\n"
            "    print(i)\n"
        )
        result = self.detector.detectPythonInString(text, verbose=False)
        self.assertIn("<PythonCode>", result,
                      "Expected partial parse to salvage enough code for detection.")
        self.assertNotEqual(text, result,
                            "Should have wrapped the code block or changed the wrap scoring.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_partial_syntax_error_code: SUCCESS")

    def test_too_short_string(self):
        """
        Very short strings should not be considered as containing code.
        """
        text = "Hi"
        result = self.detector.detectPythonInString(text, verbose=False)
        self.assertEqual(text, result, "Short text should remain unchanged (no wrap expected).")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_too_short_string: SUCCESS")

    def test_multiple_code_blocks_in_string(self):
        """
        Verify that multiple code blocks in a single string are all detected and wrapped.
        """
        text = (
            "First snippet:\n"
            "def alpha():\n"
            "    pass\n\n"
            "Second snippet:\n"
            "for i in range(3):\n"
            "    print(i)\n\n"
            "Non-code text in between.\n"
        )
        result = self.detector.detectPythonInString(text, verbose=False)
        # Expect at least two separate code blocks wrapped.
        self.assertTrue(result.count("<PythonCode>") >= 2,
                        "Expected at least two code blocks to be wrapped.")
        self.assertTrue(result.count("</PythonCode>") >= 2,
                        "Expected closing tags for each code block.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_multiple_code_blocks_in_string: SUCCESS")

    def test_intricated_but_not_python(self):
        """
        This snippet tries to mimic Python with indentation/colons,
        but it's actually NOT valid Python (missing real keywords, etc.)
        We want to ensure the detector does NOT wrap it.
        """
        text = (
            "Pretend code:\n"
            "  d3f xColor(): # not actually def\n"
            "  st@t x= @some-other-thing\n"
            "  ends.\n"
        )
        result = self.detector.detectPythonInString(text, verbose=False)
        self.assertEqual(text, result,
                         "Tricky snippet is not real Python and should remain unwrapped.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_intricated_but_not_python: SUCCESS")

    ########################################################################
    # non malicious tests (JSON str)
    ########################################################################
    def test_json_pure_text_no_code(self):
        """
        Same as 'test_pure_text_no_code', but now embedded in JSON
        with a nested structure.
        Should remain unmodified (no <PythonCode> tags).
        """
        data = {
            "level1": {
                "description": "Hello world. This is purely a normal sentence. 12345? Yes!"
            },
            "other_key": "Still no code here."
        }
        input_json = json.dumps(data)
        result_json = self.detector.detectPythonCodeInJson(input_json, verbose=False)
        self.assertEqual(result_json, input_json,
                         "Pure text in nested JSON must remain unchanged.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False.")
        print("test_json_pure_text_no_code: SUCCESS")

    def test_json_with_code(self):
        """
        Verify that a JSON string field containing Python code is processed and wrapped.
        """
        data = {
            "info": "Some informational text.",
            "snippet": "def foo():\n    return 42\n"
        }
        input_json = json.dumps(data)
        result_json = self.detector.detectPythonCodeInJson(input_json, verbose=False)
        self.assertIn("<PythonCode>", result_json, "Expected code snippet to be wrapped in JSON field.")
        self.assertIn("</PythonCode>", result_json, "Expected closing wrap tag in JSON field.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False.")
        print("test_json_with_code: SUCCESS")

    def test_json_threshold_revert(self):
        """
        Increase the threshold so that even valid code does not meet it,
        causing a revert to the original JSON.
        """
        self.detector.stat_threshold = 90.0  # Force a high threshold
        data = {
            "text": "print('Hello')",  # valid code, but should not meet the high threshold
        }
        input_json = json.dumps(data)
        result_json = self.detector.detectPythonCodeInJson(input_json, verbose=False)
        self.assertEqual(result_json, input_json,
                         "Should revert to original JSON if confidence is below the threshold.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_json_threshold_revert: SUCCESS")

    def test_json_list_parallel_processing(self):
        """
        Verify that parallel processing of a JSON list handles multiple code-containing strings.
        """
        data = [
            "def function_one():\n    pass\n",
            "class MyClass:\n    def method(self):\n        return 1\n",
            "No code here though"
        ]
        input_json = json.dumps(data)
        result_json = self.detector.detectPythonCodeInJson(input_json, verbose=False, parallel=True)
        self.assertIn("<PythonCode>", result_json,
                      "Parallel detection should find at least one code block in the list.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_json_list_parallel_processing: SUCCESS")



    def test_intricated_disguised_python(self):
        """
        An 'intricated' snippet that doesn't look obviously like Python
        at first glance, but does indeed contain Python code.
        Should be recognized & wrapped if our heuristics are correct.
        """
        text = (
            "Look at this weird snippet:\n"
            "  def hidden_func ():\n"
            "     x=3\n"
            "     if x>2:\n"
            "         print('caught you')\n"
            "All done.\n"
        )
        result = self.detector.detectPythonInString(text, verbose=False)
        self.assertIn("<PythonCode>", result,
                      "Even though it's disguised, real python code should be detected & wrapped.")
        self.assertIn("</PythonCode>", result,
                      "Closing code tag must exist as well.")
        # well this is not because it's intricated, that it's dangerous
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_intricated_disguised_python: SUCCESS")



    def test_json_javascript_snippet(self):
        """
        A snippet containing JavaScript code, but stored in a JSON structure.
        Should NOT be wrapped as Python.
        """
        data = {
            "script": "function greet(name) {\n    console.log('Hello, ' + name);\n}\n",
            "meta": {
                "lang": "js"
            }
        }
        input_json = json.dumps(data)
        result_json = self.detector.detectPythonCodeInJson(input_json, verbose=False)
        # We do NOT expect <PythonCode> tags.
        self.assertEqual(result_json, input_json, "JS snippet in JSON should remain unchanged.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_json_javascript_snippet: SUCCESS")

    def test_json_intricated_disguised_python(self):
        """
        JSON version of the 'intricated_disguised_python' test:
        Should detect & wrap the disguised python code if heuristics are correct.
        """
        data = {
            "weird_data": [
                "No code in this list item",
                "Look at this weird snippet:\n  def hidden_func ():\n     x=3\n     if x>2:\n         print('caught you')\nAll done.\n",
                "Just some plain text here too"
            ]
        }
        input_json = json.dumps(data)
        result_json = self.detector.detectPythonCodeInJson(input_json, verbose=False)
        # The disguised snippet should be detected & wrapped.
        self.assertIn("<PythonCode>", result_json,
                      "Disguised Python code in a JSON list should be detected & wrapped.")
        self.assertIn("</PythonCode>", result_json, "Expected the closing wrap tag as well.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_json_intricated_disguised_python: SUCCESS")

    def test_json_intricated_but_not_python(self):
        """
        JSON version of the 'intricated_but_not_python' test:
        Should verify that nonsense code is NOT detected & wrapped.
        """
        data = {
            "fake_snippet": "Pretend code:\n  d3f xColor(): # not actually def\n  st@t x= @some-other-thing\n  ends.\n",
            "some_other_key": "Just normal text"
        }
        input_json = json.dumps(data)
        result_json = self.detector.detectPythonCodeInJson(input_json, verbose=False)
        self.assertEqual(result_json, input_json,
                         "Tricky but invalid python-like code in JSON must remain unwrapped.")
        self.assertFalse(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be False."
        )
        print("test_json_intricated_but_not_python: SUCCESS")

    ########################################################################
    # security tests (Dangerous code should stay wrapped)
    ########################################################################

    def test_dangerous_code_must_stay_wrapped(self):
        """
        Verify that if the snippet is recognized as dangerous (e.g. uses os.system),
        the code remains wrapped in <PythonCode> and sets dangerous_code_detected = True.
        """
        # We keep the threshold at 40.0 in setUp(), which is low enough to detect multi-line code.
        text = (
            "def malicious_func():\n"
            "    import os\n"
            "    os.system('rm -rf /')\n"
        )
        result = self.detector.detectPythonInString(text, verbose=False)

        # Check that it indeed got wrapped (confidence should be high enough for multi-line)
        self.assertIn("<PythonCode>", result, "Dangerous code must be wrapped in <PythonCode> tags.")
        self.assertIn("</PythonCode>", result, "Closing tag should be present.")

        # Check that the dangerous_code_detected flag is True
        self.assertTrue(
            self.detector.dangerous_code_detected,
            "Dangerous code => dangerous_code_detected must be True."
        )
        print("test_dangerous_code_must_stay_wrapped: SUCCESS")


if __name__ == "__main__":
    # Run all tests in verbose mode so you can see each test name + success
    unittest.main(verbosity=2)
