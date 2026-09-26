"""Facts about a codebase for explaining it (``kingmadoc explain facts``).

What can be read from the code deterministically, so an agent draws its diagrams from
facts instead of guesses: the project references, the data model from ORM code, and
what a branch changed. The parsers are pure; ``collect`` does the reading and git calls.
"""
