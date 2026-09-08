"""Application-level AI use cases — orchestrates the preprocessing and
provider layers into single-purpose service methods. Contains no LLM
SDK code, no prompt definitions, and no database access; those belong
to app/ai/providers/, app/ai/prompts/, and a future persistence layer
respectively.
"""
