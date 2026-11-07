"""Compare a case's expected states with the reference model."""

from ansitest.model import visible
from ansitest.sgr import runs


def model_mismatch(case) -> str | None:
    """None if the reference model, applied to the payload, gives the
    expected text and states; else a description of the first difference."""
    result, _ = runs(case.payload.decode("utf-8", "surrogateescape"))
    model = [(char, state) for text, state in result for char in visible(text)]
    expected = [(char, state) for text, state in case.expect for char in text]
    model_text = "".join(char for char, _ in model)
    if model_text != case.expected_text():
        return f"text: model {model_text!r}, expected {case.expected_text()!r}"
    for (char, state), (_, wanted) in zip(model, expected):
        if wanted is not None and state != wanted:
            return f"{char!r}: model {state}, expected {wanted}"
    return None
